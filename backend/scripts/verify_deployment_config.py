#!/usr/bin/env python3
"""Verify deployment configuration for drama-processor-job.

This script checks that the deployment configuration matches the expected values.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def verify_deployment_config():
    """Verify deployment configuration."""
    
    print("=" * 80)
    print("Deployment Configuration Verification")
    print("=" * 80)
    
    workflow_file = Path(__file__).parent.parent.parent / ".github" / "workflows" / "backend-deploy.yaml"
    
    if not workflow_file.exists():
        print(f"❌ Workflow file not found: {workflow_file}")
        return 1
    
    content = workflow_file.read_text()
    
    # Find Processor Worker Job deployment section
    processor_section_match = re.search(
        r"Deploy Processor Worker Job.*?\n(.*?)(?=\n\s+- name:|\Z)",
        content,
        re.DOTALL
    )
    
    if not processor_section_match:
        print("❌ Could not find Processor Worker Job deployment section")
        return 1
    
    processor_section = processor_section_match.group(1)
    
    print(f"\n{'-' * 80}")
    print(f"Processor Worker Job Configuration")
    print(f"{'-' * 80}")
    
    # Check each parameter
    checks = [
        ("--memory", r"--memory\s+4Gi", "4Gi", "Memory should be 4Gi"),
        ("--cpu", r"--cpu\s+2", "2", "CPU should be 2"),
        ("--parallelism", r"--parallelism\s+50", "50", "Parallelism should be 50"),
        ("--task-timeout", r"--task-timeout\s+7200", "7200", "Task timeout should be 7200 seconds (2h)"),
    ]
    
    all_passed = True
    
    for param_name, pattern, expected_value, description in checks:
        match = re.search(pattern, processor_section)
        if match:
            print(f"  ✅ {param_name}: {expected_value} - {description}")
        else:
            print(f"  ❌ {param_name}: NOT FOUND or INCORRECT - {description}")
            all_passed = False
    
    # Show the actual configuration section
    print(f"\n{'-' * 80}")
    print(f"Actual Configuration Section")
    print(f"{'-' * 80}")
    lines = processor_section.strip().split('\n')
    for line in lines[:15]:  # Show first 15 lines
        print(f"  {line}")
    
    # Summary
    print(f"\n{'=' * 80}")
    print(f"Verification Summary")
    print(f"{'=' * 80}")
    
    if all_passed:
        print(f"✅ All deployment configuration checks passed!")
        print(f"\n📋 Expected Configuration:")
        print(f"   --memory 4Gi (was 32Gi)")
        print(f"   --cpu 2 (was 8)")
        print(f"   --parallelism 50 (was 5)")
        print(f"   --task-timeout 7200 (was 86400, i.e., 2h instead of 24h)")
        return 0
    else:
        print(f"❌ Some configuration checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(verify_deployment_config())


