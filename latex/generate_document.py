"""
Document Token Generator
Injects a tracking token into the LaTeX document template and compiles a versioned PDF.

Usage:
    python latex/generate_document.py --recipient "Hays" --token abc123ef
    python latex/generate_document.py --recipient "TCS via Avance" --auto-token

Requirements:
    - XeLaTeX installed (for Inconsolata font)
    - template_a.tex in the same directory
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATHS = {
    "a": os.path.join(SCRIPT_DIR, "template_a.tex"),
    "b": os.path.join(SCRIPT_DIR, "template_b.tex"),
}
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
BASE_URL = os.environ.get("TRACKER_BASE_URL", "https://your-tracker-host.example.com")


def generate_token(label: str) -> str:
    raw = f"{label}-{time.time()}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def make_url(slug: str, token: str) -> str:
    return f"{BASE_URL}/r/{slug}?t={token}"


def build_tex(token: str, template_path: str) -> str:
    with open(template_path, "r") as f:
        content = f.read()

    # Replace all placeholder URLs with tracked versions
    replacements = {
        "%%TRACKER_GH%%":         make_url("gh", token),
        "%%TRACKER_LI%%":         make_url("li", token),
        "%%TRACKER_DEMO_CNN%%":   make_url("demo/cnn", token),
        "%%TRACKER_DEMO_RAG%%":   make_url("demo/rag", token),
        "%%TRACKER_DEMO_REC%%":   make_url("demo/rec", token),
        "%%TRACKER_DEMO_AWC%%":   make_url("demo/awc", token),
        "%%TRACKER_REPO_AWC%%":   make_url("repo/awc", token),
        "%%TRACKER_REPO_CNN%%":   make_url("repo/cnn", token),
        "%%TRACKER_REPO_RAG%%":   make_url("repo/rag", token),
        "%%TRACKER_REPO_REC%%":   make_url("repo/rec", token),
        "%%TRACKER_REPO_POSHAN%%":make_url("repo/poshan", token),
        "%%TOKEN%%":              token,
    }

    for placeholder, url in replacements.items():
        content = content.replace(placeholder, url)

    return content


def compile(tex_content: str, token: str, label: str, track: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_label = label.replace(" ", "_").replace("/", "-")
    prefix = "IpsitMohanty_Doc_B" if track == "b" else "IpsitMohanty_Doc"
    filename = f"{prefix}_{safe_label}_{token}"
    tex_path = os.path.join(OUTPUT_DIR, f"{filename}.tex")
    pdf_path = os.path.join(OUTPUT_DIR, f"{filename}.pdf")

    with open(tex_path, "w") as f:
        f.write(tex_content)

    result = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", f"{filename}.tex"],
        cwd=OUTPUT_DIR,
        capture_output=True,
        text=True,
    )

    # Run twice for proper rendering
    subprocess.run(
        ["xelatex", "-interaction=nonstopmode", f"{filename}.tex"],
        cwd=OUTPUT_DIR,
        capture_output=True,
        text=True,
    )

    if not os.path.exists(pdf_path):
        print("ERROR: PDF compilation failed.")
        print(result.stdout[-2000:])
        sys.exit(1)

    # Clean aux files
    for ext in [".aux", ".log", ".out"]:
        aux = os.path.join(OUTPUT_DIR, f"{filename}{ext}")
        if os.path.exists(aux):
            os.remove(aux)

    return pdf_path


def main():
    parser = argparse.ArgumentParser(description="Generate tracked document PDF")
    parser.add_argument("--recipient", required=True, help="Recipient label e.g. 'Hays'")
    parser.add_argument("--token", help="Explicit token (8 chars hex). If omitted, auto-generated.")
    parser.add_argument("--auto-token", action="store_true", help="Auto-generate token")
    parser.add_argument(
        "--track",
        choices=["a", "b"],
        default="a",
        help="Document variant: 'a' (Data & ML Engineer, default) or 'b' (Program Management & Consulting)",
    )
    args = parser.parse_args()

    token = args.token if args.token else generate_token(args.recipient)
    token = token[:8]  # enforce 8 char max
    template_path = TEMPLATE_PATHS[args.track]

    print(f"\n{'='*50}")
    print(f"  Recipient : {args.recipient}")
    print(f"  Track     : {args.track}")
    print(f"  Token     : {token}")
    print(f"  Base URL  : {BASE_URL}")
    print(f"{'='*50}\n")

    print("Building LaTeX...")
    tex = build_tex(token, template_path)

    if shutil.which("xelatex"):
        print("Compiling PDF...")
        pdf = compile(tex, token, args.recipient, args.track)
        print(f"\n[OK] PDF ready: {pdf}")
    else:
        # Save just the .tex if xelatex not available
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        safe = args.recipient.replace(" ", "_").replace("/", "-")
        prefix = "IpsitMohanty_Doc_B" if args.track == "b" else "IpsitMohanty_Doc"
        tex_out = os.path.join(OUTPUT_DIR, f"{prefix}_{safe}_{token}.tex")
        with open(tex_out, "w") as f:
            f.write(tex)
        print(f"\n[OK] LaTeX ready (xelatex not found, compile manually): {tex_out}")

    print(f"\nTracking URLs for token [{token}]:")
    slugs = ["gh", "li", "demo/cnn", "demo/rag", "demo/rec", "demo/awc",
             "repo/awc", "repo/cnn", "repo/rag", "repo/rec", "repo/poshan"]
    for slug in slugs:
        print(f"  {slug:<20} -> {make_url(slug, token)}")

    print(f"\nAdd to DB:")
    print(f"  INSERT INTO recipients (token, label) VALUES ('{token}', '{args.recipient}');")
    print()


if __name__ == "__main__":
    main()
