"""
Builds data/manifest.json by combining:
  - the existing papersdb repo's native file tree (already-hosted PDFs)
  - the THSC Year-12 Trial crawl (external link-only entries, for subjects
    papersdb does not already host)

This is a from-scratch rebuild script, not something that runs automatically --
data/manifest.json is already committed and is the source of truth for the site.
To regenerate it you need two raw inputs that aren't checked in (they're large,
disposable scrape artifacts, not canonical data):

  1. This repo's own file tree, e.g.:
     curl -s "https://api.github.com/repos/<owner>/<repo>/git/trees/main?recursive=true" \
       > scripts/raw/papersdb_tree.json

  2. A recursive crawl of https://thsc.zaxu.xyz/Year%2012/Trial/ (h5ai directory
     listing -- each folder's HTML has rows of the form
     `<a href="...">name</a></td><td class="fb-d">modified</td><td class="fb-s">size</td>`)
     saved in the shape {"tree": {"_dirs": {name: {...}}, "_files": [{"name","url",
     "size","modified"}]}}} to scripts/raw/thsc_year12_trial.json.

Then run from the repo root:
    python scripts/generate_manifest.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "scripts", "raw")

NATIVE_TREE_PATH = os.path.join(RAW, "papersdb_tree.json")
THSC_TREE_PATH = os.path.join(RAW, "thsc_year12_trial.json")
OUT_PATH = os.path.join(HERE, "data", "manifest.json")

# Faculty/subject folder name (as it appears on thsc.zaxu.xyz) -> clean subject display name.
# Subjects already natively hosted by papersdb are intentionally excluded here (Biology,
# Chemistry, Physics, Mathematics 2U/3U/4U/Standard) -- those keep their existing native
# content untouched; we only note an external "more trials" link for them.
SUBJECT_MAP = {
    ("CAFS", None): "Community and Family Studies",
    ("English", "Paper 1"): "English (Paper 1)",
    ("English", "Paper 2"): "English (Paper 2)",
    ("HSIE", "Business Studies"): "Business Studies",
    ("HSIE", "Economics"): "Economics",
    ("HSIE", "Legal Studies"): "Legal Studies",
    ("HSIE", "SOR 1"): "Studies of Religion I",
    ("HSIE", "SOR 2"): "Studies of Religion II",
    ("PDHPE", None): "PDHPE",
    ("Science", "Earth & Environmental Science"): "Earth and Environmental Science",
    ("Science", "Senior Science"): "Senior Science",
    ("TAS", "Agriculture"): "Agriculture",
    ("TAS", "Engineering Studies"): "Engineering Studies",
    ("TAS", "IPT"): "Information Processes and Technology",
    ("TAS", "SDD"): "Software Design and Development",
}

# History needs a third level (Ancient History / Modern History / History Extension)
HISTORY_MAP = {
    "Ancient History": "Ancient History",
    "Modern History": "Modern History",
    "History Extension": "History Extension",
}

# Subjects papersdb already natively hosts -- we skip rebuilding these from THSC,
# but still want to surface a single "more trial papers on THSC" link for each.
NATIVE_EXTERNAL_LINKS = {
    "Biology": "https://thsc.zaxu.xyz/Year%2012/Trial/Science/Biology/",
    "Chemistry": "https://thsc.zaxu.xyz/Year%2012/Trial/Science/Chemistry/",
    "Physics": "https://thsc.zaxu.xyz/Year%2012/Trial/Science/Physics/",
    "Mathematics Advanced": "https://thsc.zaxu.xyz/Year%2012/Trial/Maths/2U/",
    "Mathematics Extension 1": "https://thsc.zaxu.xyz/Year%2012/Trial/Maths/3U/",
    "Mathematics Extension 2": "https://thsc.zaxu.xyz/Year%2012/Trial/Maths/4U/",
    "Mathematics Standard": "https://thsc.zaxu.xyz/Year%2012/Trial/Maths/Standard/",
}


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s


def build_native_subjects():
    with open(NATIVE_TREE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    tree = data["tree"]
    blobs = [t for t in tree if t["type"] == "blob" and t["path"].lower().endswith(".pdf")]

    subjects = {}
    for b in blobs:
        parts = b["path"].split("/")
        subject = parts[0]
        intermediate = parts[1:-1]  # everything between subject and filename, 1..N folders deep
        entry = {
            "title": parts[-1][:-4],
            "url": b["path"].replace(" ", "%20"),
            "size": b["size"],
        }
        subjects.setdefault(subject, {"byCategory": {}})
        if len(intermediate) <= 1:
            # <Subject>/<Category>/<file>.pdf  (no school level, e.g. HSC past papers)
            category = intermediate[0] if intermediate else "Other"
            subjects[subject]["byCategory"].setdefault(category, {"flat": [], "schools": {}})
            subjects[subject]["byCategory"][category]["flat"].append(entry)
        else:
            # <Subject>/<Category>/[.../]<School>/<file>.pdf -- any extra folders between
            # category and school (e.g. "Y11 Internals/Preliminary HY") get folded into the
            # category label; the LAST intermediate folder is always treated as the school.
            category = " / ".join(intermediate[:-1])
            school = intermediate[-1]
            subjects[subject]["byCategory"].setdefault(category, {"flat": [], "schools": {}})
            subjects[subject]["byCategory"][category]["schools"].setdefault(school, []).append(entry)

    out = []
    for name, data in sorted(subjects.items()):
        categories = []
        for cat_name, cat in sorted(data["byCategory"].items()):
            categories.append({
                "name": cat_name,
                "papers": cat["flat"],
                "schools": [
                    {"name": sch, "papers": papers}
                    for sch, papers in sorted(cat["schools"].items())
                ],
            })
        out.append({
            "name": name,
            "slug": slugify(name),
            "native": True,
            "externalMoreUrl": NATIVE_EXTERNAL_LINKS.get(name),
            "categories": categories,
        })
    return out


def walk_thsc(node):
    """Yield (school_name_or_None, file_entry) for every file under this node, recursing."""
    for f in node.get("_files", []):
        yield None, f
    for child_name, child in node.get("_dirs", {}).items():
        for school, f in walk_thsc(child):
            yield (school or child_name), f


def build_external_subjects():
    if not os.path.exists(THSC_TREE_PATH):
        print("WARNING: THSC crawl data not found yet, skipping external subjects:", THSC_TREE_PATH)
        return []
    with open(THSC_TREE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    root = data["tree"]  # dirs keyed by faculty (CAFS, English, HSIE, Maths, PDHPE, Science, TAS, ...)

    collected = {}  # display name -> {school: [papers]}

    def add_paper(display_name, school, f):
        collected.setdefault(display_name, {}).setdefault(school or "General", []).append({
            "title": f["name"][:-4] if f["name"].lower().endswith(".pdf") else f["name"],
            "url": f["url"],
            "size": f.get("size", ""),
            "modified": f.get("modified", ""),
        })

    for faculty, fnode in root.get("_dirs", {}).items():
        if faculty == "English":
            # English/<Paper>/<era-or-level>/<School>/file.pdf
            for paper_name, pnode in fnode.get("_dirs", {}).items():
                display = SUBJECT_MAP.get(("English", paper_name))
                if not display:
                    continue
                for school, f in walk_thsc(pnode):
                    add_paper(display, school, f)
            continue

        if faculty in ("CAFS", "PDHPE"):
            display = SUBJECT_MAP.get((faculty, None))
            if display:
                for school, f in walk_thsc(fnode):
                    add_paper(display, school, f)
            continue

        # Faculty with a subject sub-level (HSIE, Science, TAS); Maths handled as native, skipped.
        for subject_name, snode in fnode.get("_dirs", {}).items():
            if faculty == "HSIE" and subject_name == "History":
                for subsub, ssnode in snode.get("_dirs", {}).items():
                    display = HISTORY_MAP.get(subsub)
                    if not display:
                        continue
                    for school, f in walk_thsc(ssnode):
                        add_paper(display, school, f)
                continue
            display = SUBJECT_MAP.get((faculty, subject_name))
            if not display:
                continue  # either unmapped or a subject papersdb already natively hosts (Maths etc.)
            for school, f in walk_thsc(snode):
                add_paper(display, school, f)

    out = []
    for display_name, schools in sorted(collected.items()):
        out.append({
            "name": display_name,
            "slug": slugify(display_name),
            "native": False,
            "source": "THSC Online (community mirror: thsc.zaxu.xyz)",
            "categories": [{
                "name": "Trials",
                "papers": [],
                "schools": [
                    {"name": sch, "papers": papers}
                    for sch, papers in sorted(schools.items())
                ],
            }],
        })
    return out


def paper_count(subject):
    return sum(len(c["papers"]) for c in subject["categories"]) + \
        sum(len(sc["papers"]) for c in subject["categories"] for sc in c["schools"])


def school_count(subject):
    names = set()
    for c in subject["categories"]:
        for sc in c["schools"]:
            names.add(sc["name"])
    return len(names)


def main():
    native = build_native_subjects()
    external = build_external_subjects()
    all_subjects = native + external

    out_dir = os.path.dirname(OUT_PATH)
    subjects_dir = os.path.join(out_dir, "subjects")
    os.makedirs(subjects_dir, exist_ok=True)

    index = []
    for s in all_subjects:
        index.append({
            "name": s["name"],
            "slug": s["slug"],
            "native": s["native"],
            "source": s.get("source"),
            "externalMoreUrl": s.get("externalMoreUrl"),
            "paperCount": paper_count(s),
            "schoolCount": school_count(s),
        })
        with open(os.path.join(subjects_dir, s["slug"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(s, f, separators=(",", ":"))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"subjects": sorted(index, key=lambda s: s["name"])}, f, indent=1)

    total_papers = sum(
        len(sc["papers"]) for s in external for sc in s["categories"][0]["schools"]
    )
    total_schools = sum(len(s["categories"][0]["schools"]) for s in external)
    print(f"Wrote {OUT_PATH} and {len(all_subjects)} files under {subjects_dir}")
    print(f"  native subjects: {len(native)}")
    print(f"  external subjects: {len(external)} ({total_schools} school groups, {total_papers} papers)")


if __name__ == "__main__":
    main()
