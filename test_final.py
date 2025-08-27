#!/usr/bin/env python3
"""
Final test to validate the corrected transformation
"""

import asyncio
import tempfile
from pathlib import Path
from PIL import Image
from svg_processor import SVGProcessor

async def validate_results():
    """Test the corrected transformation and validate results"""
    
    expected_results = [
        {
            "name": "Image 1 (DFC9A2C6)",
            "expected_aspect": 1.500,  # From our calculation: 4031.8/2687.9
            "tolerance": 0.1
        },
        {
            "name": "Image 2 (IMG_9420)", 
            "expected_aspect": 1.499,  # From debug: 5147.5/3431.7
            "tolerance": 0.1
        },
        {
            "name": "Image 3 (IMG_1982)",
            "expected_aspect": 1.499,  # Similar to Image 2
            "tolerance": 0.1
        }
    ]
    
    print("=== FINAL VALIDATION TEST ===\n")
    
    async with SVGProcessor() as processor:
        with tempfile.TemporaryDirectory() as temp_dir:
            print("Processing SVG...")
            result = await processor.process_svg_async(
                'https://fpd-exporter-staging-v2.s3.amazonaws.com/775cb0b423bf1151fd6b80065102535f264873c8-e41cfa57-f349-4239-82e7-f5179dba072e/uibr1017-0-combo-8_view_0.svg', 
                Path(temp_dir)
            )
            
            print(f"Processing result: {result}")
            
            if result['success']:
                temp_path = Path(temp_dir)
                crop_files = sorted(temp_path.glob('crop_*.png'))
                
                print(f"\nFound {len(crop_files)} crop files")
                
                all_passed = True
                for i, file in enumerate(crop_files):
                    if i < len(expected_results):
                        expected = expected_results[i]
                        
                        with Image.open(file) as img:
                            actual_ratio = img.size[0] / img.size[1] if img.size[1] > 0 else 0
                            diff = abs(actual_ratio - expected['expected_aspect'])
                            passed = diff <= expected['tolerance']
                            
                            print(f"\n{expected['name']}:")
                            print(f"  File: {file.name}")
                            print(f"  Size: {img.size}")
                            print(f"  Actual ratio: {actual_ratio:.3f}")
                            print(f"  Expected ratio: {expected['expected_aspect']:.3f}")
                            print(f"  Difference: {diff:.3f}")
                            print(f"  Result: {'✅ PASS' if passed else '❌ FAIL'}")
                            
                            if not passed:
                                all_passed = False
                
                print(f"\n{'='*50}")
                print(f"OVERALL RESULT: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
                print(f"{'='*50}")
                
            else:
                print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(validate_results())