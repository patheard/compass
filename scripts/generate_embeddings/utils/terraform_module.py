#!/usr/bin/env python3
"""
Terraform module detection and download utility.
"""

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def detect_terraform_modules(text: str) -> list[dict[str, str]]:
    """Detect Terraform module declarations in text.

    Args:
        text: Text content to scan for module blocks

    Returns:
        List of dicts with 'name' and 'source' keys for each detected module
    """
    modules = []

    # Pattern to match module blocks with source attribute
    # We need to handle nested braces
    module_pattern = r'module\s+"([^"]+)"\s*\{'

    matches = re.finditer(module_pattern, text, re.DOTALL)

    for match in matches:
        module_name = match.group(1)
        start_pos = match.end()

        # Find the matching closing brace by counting brace depth
        brace_count = 1
        end_pos = start_pos

        while end_pos < len(text) and brace_count > 0:
            if text[end_pos] == "{":
                brace_count += 1
            elif text[end_pos] == "}":
                brace_count -= 1
            end_pos += 1

        # Extract the module block content
        module_content = text[start_pos : end_pos - 1]

        # Look for source attribute within this module block
        source_pattern = r'source\s*=\s*"([^"]+)"'
        source_match = re.search(source_pattern, module_content)

        if source_match:
            source = source_match.group(1)
            modules.append({"name": module_name, "source": source})
            logger.debug(f"Detected module '{module_name}' with source '{source}'")

    return modules


def download_terraform_module(
    source: str, download_dir: Path, module_name: str
) -> Path | None:
    """Download a Terraform module from its source.

    Args:
        source: Module source (git URL, local path, or Terraform registry)
        download_dir: Directory to download the module to
        module_name: Name of the module (for logging)

    Returns:
        Path to the downloaded module directory, or None if download failed
    """
    try:
        # Handle different source types
        if (
            source.startswith("github.com")
            or source.startswith("git::")
            or source.startswith("git@")
            or ".git" in source
        ):
            return _download_git_module(source, download_dir, module_name)
        elif source.startswith("./") or source.startswith("../"):
            logger.info(f"Module '{module_name}' uses relative path: {source}")
            return None  # Can't download relative paths without context
        elif source.startswith("/"):
            logger.info(f"Module '{module_name}' uses absolute path: {source}")
            # Could potentially copy if the path exists, but skip for now
            return None
        elif source.count("/") >= 1 and "://" not in source:
            # Terraform registry format: namespace/name/provider or namespace/name
            return _download_registry_module(source, download_dir, module_name)
        else:
            logger.warning(f"Unsupported module source format: {source}")
            return None

    except Exception as e:
        logger.error(f"Failed to download module '{module_name}' from {source}: {e}")
        return None


def _download_git_module(
    source: str, download_dir: Path, module_name: str
) -> Path | None:
    """Download a Terraform module from a git repository.

    Args:
        source: Git URL (e.g., git::https://... or git@...)
        download_dir: Directory to download to
        module_name: Name of the module

    Returns:
        Path to downloaded module or None if failed
    """
    # Remove git:: prefix if present
    git_url = source.replace("git::", "")

    # Handle ref parameter (e.g., ?ref=v1.0.0)
    ref = None
    if "?ref=" in git_url:
        git_url, ref_part = git_url.split("?ref=", 1)
        ref = ref_part.split("&")[0]  # In case there are other params

    # Handle subdirectory (e.g., //subdir)
    subdir = None
    if "//" in git_url:
        git_url, subdir = git_url.split("//", 1)

    # Handle GitHub URLs without scheme
    if git_url.startswith("github.com"):
        git_url = f"https://{git_url}.git"

    print(
        f"Downloading git module '{module_name}' from {git_url} (ref={ref}, subdir={subdir})"
    )

    module_dir = download_dir / module_name

    try:
        # Clone the repository
        cmd = ["git", "clone", "--depth", "1"]
        if ref:
            cmd.extend(["--branch", ref])
        cmd.extend([git_url, str(module_dir)])

        logger.info(f"Cloning git module: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # If there's a subdirectory, move its contents up
        if subdir:
            subdir_path = module_dir / subdir
            if subdir_path.exists():
                # Move contents to a temp dir, then back
                temp_dir = module_dir.parent / f"{module_name}_temp"
                shutil.move(str(subdir_path), str(temp_dir))
                shutil.rmtree(module_dir)
                shutil.move(str(temp_dir), str(module_dir))

        logger.info(f"Successfully downloaded git module '{module_name}'")
        return module_dir

    except subprocess.CalledProcessError as e:
        logger.error(f"Git clone failed for '{module_name}': {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Error processing git module '{module_name}': {e}")
        return None


def _download_registry_module(
    source: str, download_dir: Path, module_name: str
) -> Path | None:
    """Download a Terraform module from the Terraform Registry.

    Args:
        source: Registry path (e.g., terraform-aws-modules/vpc/aws)
        download_dir: Directory to download to
        module_name: Name of the module

    Returns:
        Path to downloaded module or None if failed
    """
    # For Terraform registry modules, we need to construct the git URL
    # Format: namespace/name/provider or namespace/name
    parts = source.split("/")

    if len(parts) < 2:
        logger.error(f"Invalid registry module format: {source}")
        return None

    # Most Terraform registry modules are on GitHub
    # terraform-aws-modules/vpc/aws -> https://github.com/terraform-aws-modules/terraform-aws-vpc
    if len(parts) == 3:
        namespace, name, provider = parts
        # Common pattern: namespace/terraform-provider-name
        git_url = f"https://github.com/{namespace}/terraform-{provider}-{name}.git"
    else:
        namespace, name = parts[:2]
        git_url = f"https://github.com/{namespace}/{name}.git"

    logger.info(
        f"Attempting to download registry module '{source}' from inferred URL: {git_url}"
    )

    return _download_git_module(git_url, download_dir, module_name)


def read_downloaded_module_files(module_dir: Path) -> list[tuple[Path, str]]:
    """Read all .tf files from a downloaded module directory.

    Args:
        module_dir: Path to the module directory

    Returns:
        List of tuples (file_path, file_content) for each .tf file
    """
    files = []

    if not module_dir.exists():
        logger.warning(f"Module directory does not exist: {module_dir}")
        return files

    # Find all .tf files
    for tf_file in module_dir.rglob("*.tf"):
        try:
            with open(tf_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                files.append((tf_file, content))
                logger.debug(f"Read module file: {tf_file}")
        except Exception as e:
            logger.warning(f"Failed to read module file {tf_file}: {e}")

    return files


if __name__ == "__main__":
    # Test module detection
    test_terraform = """
    module "vpc" {
      source  = "terraform-aws-modules/vpc/aws"
      version = "~> 3.0"
      
      name = "my-vpc"
      cidr = "10.0.0.0/16"
    }
    
    module "security_group" {
      source = "git::https://github.com/terraform-aws-modules/terraform-aws-security-group.git?ref=v4.0.0"
      
      name = "my-sg"
    }
    """

    print("Testing module detection:")
    modules = detect_terraform_modules(test_terraform)
    for mod in modules:
        print(f"  - {mod['name']}: {mod['source']}")

    # Test downloading (dry run - just show what would happen)
    print("\nTesting module download (simulated):")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for mod in modules:
            print(f"\nWould download '{mod['name']}' from: {mod['source']}")
            # Uncomment to actually test download:
            # result = download_terraform_module(mod['source'], tmp_path, mod['name'])
            # if result:
            #     print(f"  Downloaded to: {result}")
            #     files = read_downloaded_module_files(result)
            #     print(f"  Found {len(files)} .tf files")
