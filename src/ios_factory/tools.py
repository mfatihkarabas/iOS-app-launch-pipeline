"""
iOS Software Factory – Custom Tools
=====================================
XcodeBuildTool  : reads output/2_Implementation.md from disk, writes Swift
                  files to the Xcode project, runs xcodebuild, returns result.
WriteSwiftFileTool: lets the agent write/overwrite a single Swift file so it
                  can fix compiler errors one file at a time (avoids token limits).
"""

import re
import subprocess
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import Field

ROOT            = Path(__file__).resolve().parents[2]
IOS_PROJECT     = ROOT / "CrewAITest" / "CrewAITest"
IOS_TESTS       = ROOT / "CrewAITest" / "CrewAITestTests"
XCODE_PROJECT   = ROOT / "CrewAITest" / "CrewAITest.xcodeproj"
IMPL_MD         = ROOT / "output" / "2_Implementation.md"

# Matches ```swift blocks whose first line is // FILE: <name>
_FILE_PATTERN = re.compile(
    r"```swift[^\n]*\n"
    r"(?://\s*filepath:[^\n]*\n)?"
    r"//\s*FILE:\s*([^\n]+)\n"
    r"(.*?)"
    r"```",
    re.DOTALL,
)


def extract_and_write_swift(markdown: str, target_dir: Path) -> list[str]:
    """Write all // FILE: blocks from markdown into target_dir. Returns filenames."""
    written: list[str] = []
    for filename, code in _FILE_PATTERN.findall(markdown):
        filename = filename.strip()
        dest = target_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code.rstrip() + "\n", encoding="utf-8")
        written.append(filename)
    return written


def _run_xcodebuild() -> str:
    """Run xcodebuild and return a clean result string."""
    try:
        result = subprocess.run(
            [
                "xcodebuild",
                "-project", str(XCODE_PROJECT),
                "-scheme", "CrewAITest",
                "-destination", "generic/platform=iOS Simulator",
                "build",
                "CODE_SIGN_IDENTITY=",
                "CODE_SIGNING_REQUIRED=NO",
                "CODE_SIGNING_ALLOWED=NO",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except FileNotFoundError:
        return "ERROR: xcodebuild not found. Make sure Xcode is installed."
    except subprocess.TimeoutExpired:
        return "ERROR: xcodebuild timed out after 180 seconds."

    if result.returncode == 0:
        return "✅ BUILD SUCCEEDED. The implementation compiles cleanly."

    lines = (result.stdout + "\n" + result.stderr).splitlines()
    errors = [l for l in lines if "error:" in l.lower()][:60]
    return "❌ BUILD FAILED.\n\nCompiler errors:\n" + "\n".join(errors)


class XcodeBuildTool(BaseTool):
    """
    Reads output/2_Implementation.md from disk, extracts all Swift files
    (// FILE: markers), writes them into CrewAITest/CrewAITest/, then runs
    xcodebuild. Returns '✅ BUILD SUCCEEDED' or '❌ BUILD FAILED' with errors.
    Call this after writing all Swift files. Use WriteSwiftFileTool to fix
    individual files before calling this again.
    """

    name: str = "xcode_build"
    description: str = (
        "Reads the Swift implementation from output/2_Implementation.md, "
        "writes all files to the Xcode project, and runs xcodebuild. "
        "Returns BUILD SUCCEEDED or BUILD FAILED with compiler errors. "
        "Input: pass any short trigger string e.g. 'run'. "
        "To fix errors: use write_swift_file to correct each broken file, "
        "then call xcode_build again."
    )

    def _run(self, trigger: str = "run") -> str:  # type: ignore[override]
        if not IMPL_MD.exists():
            return "ERROR: output/2_Implementation.md not found. Run feature_implementation first."

        markdown = IMPL_MD.read_text(encoding="utf-8")
        written = extract_and_write_swift(markdown, IOS_PROJECT)
        if not written:
            return (
                "ERROR: No '// FILE: <name>' markers found in output/2_Implementation.md.\n"
                "The implementation task must format each file as:\n"
                "```swift\n// FILE: FileName.swift\n...\n```"
            )

        result = _run_xcodebuild()
        return f"Files written: {written}\n\n{result}"


class WriteSwiftFileTool(BaseTool):
    """
    Writes a single Swift source file into CrewAITest/CrewAITest/.
    Use this to fix individual files that have compiler errors, then
    call xcode_build to verify the fix. Each call only sends one small
    file — staying well within token limits.
    """

    name: str = "write_swift_file"
    description: str = (
        "Write or overwrite a single Swift file in the Xcode project. "
        "Input must be a string in exactly this format:\n"
        "FILENAME: SomeFile.swift\n"
        "CONTENT:\n"
        "<full swift source code here>\n"
        "The file will be saved to CrewAITest/CrewAITest/SomeFile.swift."
    )

    def _run(self, input_text: str) -> str:  # type: ignore[override]
        lines = input_text.strip().splitlines()
        filename_line = next((l for l in lines if l.startswith("FILENAME:")), None)
        content_start = next((i for i, l in enumerate(lines) if l.strip() == "CONTENT:"), None)

        if not filename_line or content_start is None:
            return "ERROR: Input must start with 'FILENAME: <file>' followed by 'CONTENT:' on its own line."

        filename = filename_line.replace("FILENAME:", "").strip()
        code = "\n".join(lines[content_start + 1:])

        dest = IOS_PROJECT / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code.rstrip() + "\n", encoding="utf-8")
        return f"✅ Written: CrewAITest/CrewAITest/{filename} ({len(code.splitlines())} lines)"

