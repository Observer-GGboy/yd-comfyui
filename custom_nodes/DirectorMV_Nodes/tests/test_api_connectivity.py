#!/usr/bin/env python
"""
API Connectivity Test Script

Tests the test_connect mode for all providers.
Run from ComfyUI directory with:
    python custom_nodes/DirectorMV_Nodes/tests/test_api_connectivity.py

Environment variables required:
    - MINIMAX_API_KEY
    - KLING_API_KEY  
    - RUNWAY_API_KEY
    - VIDU_API_KEY
"""

import os
import sys

# Add parent directories to path
script_dir = os.path.dirname(os.path.abspath(__file__))
package_dir = os.path.dirname(script_dir)
nodes_dir = os.path.join(package_dir, "nodes")
sys.path.insert(0, package_dir)
sys.path.insert(0, nodes_dir)

import torch
import numpy as np
from PIL import Image
from io import BytesIO
import json


def create_test_image() -> torch.Tensor:
    """Create a simple test image tensor."""
    # Create a 512x512 RGB image
    img = Image.new("RGB", (512, 512), color=(128, 128, 200))
    np_img = np.array(img).astype(np.float32) / 255.0
    tensor = torch.from_numpy(np_img).unsqueeze(0)  # [1, H, W, C]
    return tensor


def test_provider_connect(provider: str, api_key: str = "") -> dict:
    """Test connectivity for a specific provider."""
    from api.image2video import DMV_API_Image2Video
    
    node = DMV_API_Image2Video()
    test_image = create_test_image()
    
    print(f"\n{'='*60}")
    print(f"Testing {provider.upper()} test_connect...")
    print(f"{'='*60}")
    
    try:
        video_path, task_id, cost, status, success = node.generate(
            image=test_image,
            prompt="Test prompt",
            provider=provider,
            model="auto",
            run_mode="test_connect",
            return_debug=True,
            api_key_override=api_key,
        )
        
        result = {
            "provider": provider,
            "success": success,
            "status": status,
            "cost": cost,
        }
        
        if success:
            print(f"✅ {provider}: CONNECTED")
        else:
            print(f"❌ {provider}: FAILED")
        print(f"   Status: {status}")
        
        return result
        
    except Exception as e:
        print(f"❌ {provider}: EXCEPTION - {str(e)[:100]}")
        return {
            "provider": provider,
            "success": False,
            "status": f"Exception: {str(e)[:200]}",
            "cost": 0,
        }


def test_minimax_create(api_key: str = "") -> dict:
    """Test MiniMax test_create mode."""
    from api.image2video import DMV_API_Image2Video
    
    node = DMV_API_Image2Video()
    test_image = create_test_image()
    
    print(f"\n{'='*60}")
    print("Testing MiniMax test_create...")
    print("⚠️  WARNING: This may incur a charge of ~$0.48")
    print(f"{'='*60}")
    
    try:
        video_path, task_id, cost, status, success = node.generate(
            image=test_image,
            prompt="A beautiful landscape with gentle movement",
            provider="minimax",
            model="I2V-01",
            duration="6",
            resolution="720P",
            run_mode="test_create",
            return_debug=True,
            api_key_override=api_key,
        )
        
        result = {
            "provider": "minimax",
            "mode": "test_create",
            "success": success,
            "task_id": task_id,
            "status": status,
        }
        
        if success:
            print(f"✅ MiniMax test_create: SUCCESS")
            print(f"   Task ID: {task_id}")
        else:
            print(f"❌ MiniMax test_create: FAILED")
        print(f"   Status: {status}")
        
        return result
        
    except Exception as e:
        print(f"❌ MiniMax test_create: EXCEPTION - {str(e)[:100]}")
        return {
            "provider": "minimax",
            "mode": "test_create",
            "success": False,
            "status": f"Exception: {str(e)[:200]}",
        }


def test_minimax_prod_full(api_key: str = "") -> dict:
    """Test MiniMax prod_full mode (full generation)."""
    from api.image2video import DMV_API_Image2Video
    
    node = DMV_API_Image2Video()
    test_image = create_test_image()
    
    print(f"\n{'='*60}")
    print("Testing MiniMax prod_full (FULL GENERATION)...")
    print("⚠️  WARNING: This WILL incur a charge of ~$0.48")
    print(f"{'='*60}")
    
    try:
        video_path, task_id, cost, status, success = node.generate(
            image=test_image,
            prompt="A beautiful landscape with gentle movement, peaceful atmosphere",
            provider="minimax",
            model="I2V-01",
            duration="6",
            resolution="720P",
            run_mode="prod_full",
            return_debug=True,
            api_key_override=api_key,
            enable_fallback=False,  # Don't fallback for testing
        )
        
        result = {
            "provider": "minimax",
            "mode": "prod_full",
            "success": success,
            "task_id": task_id,
            "video_path": video_path,
            "cost": cost,
            "status": status,
        }
        
        if success:
            print(f"✅ MiniMax prod_full: SUCCESS")
            print(f"   Video Path: {video_path}")
            print(f"   Cost: ${cost:.2f}")
        else:
            print(f"❌ MiniMax prod_full: FAILED")
        print(f"   Status: {status}")
        
        return result
        
    except Exception as e:
        print(f"❌ MiniMax prod_full: EXCEPTION - {str(e)[:100]}")
        return {
            "provider": "minimax",
            "mode": "prod_full",
            "success": False,
            "status": f"Exception: {str(e)[:200]}",
        }


def main():
    """Run connectivity tests."""
    print("\n" + "="*70)
    print("DirectorMV API Connectivity Test")
    print("="*70)
    
    # Check environment variables
    providers_to_test = []
    
    if os.environ.get("MINIMAX_API_KEY"):
        providers_to_test.append("minimax")
        print("✓ MINIMAX_API_KEY found")
    else:
        print("✗ MINIMAX_API_KEY not set")
    
    if os.environ.get("KLING_API_KEY"):
        providers_to_test.append("kling")
        print("✓ KLING_API_KEY found")
    else:
        print("✗ KLING_API_KEY not set")
    
    if os.environ.get("RUNWAY_API_KEY"):
        providers_to_test.append("runway")
        print("✓ RUNWAY_API_KEY found")
    else:
        print("✗ RUNWAY_API_KEY not set")
    
    if os.environ.get("VIDU_API_KEY"):
        providers_to_test.append("vidu")
        print("✓ VIDU_API_KEY found")
    else:
        print("✗ VIDU_API_KEY not set")
    
    # Always test local (no API key needed)
    providers_to_test.append("local")
    
    if len(providers_to_test) <= 1:
        print("\n⚠️  No API keys configured. Only testing local provider.")
        print("Set environment variables to test other providers:")
        print("  export MINIMAX_API_KEY='your_key'")
        print("  export KLING_API_KEY='your_key'")
        print("  export RUNWAY_API_KEY='your_key'")
        print("  export VIDU_API_KEY='your_key'")
    
    # Run tests
    results = []
    for provider in providers_to_test:
        result = test_provider_connect(provider)
        results.append(result)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    
    for r in results:
        icon = "✅" if r["success"] else "❌"
        print(f"  {icon} {r['provider']}: {'PASS' if r['success'] else 'FAIL'}")
    
    print(f"\nTotal: {passed}/{total} providers connected")
    
    # Save results to JSON
    from api.api_logger import get_api_logger
    logger = get_api_logger()
    log_path = logger.get_log_path()
    print(f"\nDetailed logs: {log_path}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test DirectorMV API connectivity")
    parser.add_argument("--minimax-create", action="store_true", 
                       help="Run MiniMax test_create (may cost ~$0.48)")
    parser.add_argument("--minimax-full", action="store_true",
                       help="Run MiniMax prod_full (will cost ~$0.48)")
    parser.add_argument("--connect-only", action="store_true",
                       help="Only run test_connect (free)")
    
    args = parser.parse_args()
    
    # Run connectivity tests
    results = main()
    
    # Additional tests if requested
    if args.minimax_create:
        print("\n" + "="*70)
        print("Running MiniMax test_create...")
        result = test_minimax_create()
        
        # Log results
        print("\n📋 test_create result:")
        print(json.dumps(result, indent=2))
    
    if args.minimax_full:
        response = input("\n⚠️  About to run prod_full which will charge ~$0.48. Continue? [y/N]: ")
        if response.lower() == "y":
            result = test_minimax_prod_full()
            
            print("\n📋 prod_full result:")
            print(json.dumps(result, indent=2))
        else:
            print("Skipped prod_full test.")

