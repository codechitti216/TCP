#!/usr/bin/env python
"""
Check TCP Model and Checkpoint Compatibility
"""

import sys
import torch
from collections import OrderedDict

# Add TCP to path
sys.path.insert(0, '.')

def check_checkpoint(checkpoint_path: str):
    """
    Check checkpoint structure and compatibility with TCP model.
    """
    print("=" * 60)
    print("TCP Checkpoint Compatibility Check")
    print("=" * 60)
    print(f"\nCheckpoint: {checkpoint_path}")
    print()
    
    # Load checkpoint
    print("[1/4] Loading checkpoint...")
    try:
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        print(f"      ✓ Checkpoint loaded successfully")
    except Exception as e:
        print(f"      ✗ Failed to load checkpoint: {e}")
        return False
    
    # Analyze checkpoint structure
    print()
    print("[2/4] Analyzing checkpoint structure...")
    print(f"      Type: {type(checkpoint)}")
    
    if isinstance(checkpoint, dict):
        print(f"      Keys: {list(checkpoint.keys())}")
        
        # Check for common checkpoint formats
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
            print(f"      ✓ Found 'state_dict' key")
        elif 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            print(f"      ✓ Found 'model_state_dict' key")
        elif 'model' in checkpoint:
            state_dict = checkpoint['model']
            print(f"      ✓ Found 'model' key")
        else:
            # Assume the checkpoint itself is the state dict
            state_dict = checkpoint
            print(f"      ℹ Checkpoint appears to be a direct state_dict")
        
        # Check for additional info
        if 'epoch' in checkpoint:
            print(f"      ℹ Epoch: {checkpoint['epoch']}")
        if 'global_step' in checkpoint:
            print(f"      ℹ Global step: {checkpoint['global_step']}")
        if 'pytorch-lightning_version' in checkpoint:
            print(f"      ℹ PyTorch Lightning version: {checkpoint['pytorch-lightning_version']}")
        if 'hyper_parameters' in checkpoint:
            print(f"      ℹ Has hyper_parameters")
    else:
        state_dict = checkpoint
        print(f"      ℹ Checkpoint is a direct state_dict")
    
    # Show state dict keys
    print()
    print("[3/4] State dict analysis...")
    print(f"      Total parameters: {len(state_dict)}")
    
    # Group by module
    modules = {}
    for key in state_dict.keys():
        parts = key.split('.')
        module = parts[0]
        if module not in modules:
            modules[module] = []
        modules[module].append(key)
    
    print(f"      Modules found:")
    for module, keys in sorted(modules.items()):
        print(f"        - {module}: {len(keys)} parameters")
    
    # Check for 'model.' prefix (PyTorch Lightning format)
    has_model_prefix = any(k.startswith('model.') for k in state_dict.keys())
    if has_model_prefix:
        print(f"      ℹ Keys have 'model.' prefix (PyTorch Lightning format)")
    
    # Load TCP model and compare
    print()
    print("[4/4] Comparing with TCP model...")
    try:
        from TCP.model import TCP
        from TCP.config import GlobalConfig
        
        config = GlobalConfig()
        model = TCP(config)
        model_state = model.state_dict()
        
        print(f"      TCP model parameters: {len(model_state)}")
        
        # Clean state dict keys (remove 'model.' prefix if present)
        cleaned_state_dict = OrderedDict()
        for k, v in state_dict.items():
            new_key = k.replace('model.', '') if k.startswith('model.') else k
            cleaned_state_dict[new_key] = v
        
        # Compare keys
        model_keys = set(model_state.keys())
        ckpt_keys = set(cleaned_state_dict.keys())
        
        matching = model_keys & ckpt_keys
        missing_in_ckpt = model_keys - ckpt_keys
        extra_in_ckpt = ckpt_keys - model_keys
        
        print(f"      Matching parameters: {len(matching)}")
        print(f"      Missing in checkpoint: {len(missing_in_ckpt)}")
        print(f"      Extra in checkpoint: {len(extra_in_ckpt)}")
        
        if missing_in_ckpt:
            print(f"\n      Missing in checkpoint (first 10):")
            for key in list(missing_in_ckpt)[:10]:
                print(f"        - {key}")
            if len(missing_in_ckpt) > 10:
                print(f"        ... and {len(missing_in_ckpt) - 10} more")
        
        if extra_in_ckpt:
            print(f"\n      Extra in checkpoint (first 10):")
            for key in list(extra_in_ckpt)[:10]:
                print(f"        - {key}")
            if len(extra_in_ckpt) > 10:
                print(f"        ... and {len(extra_in_ckpt) - 10} more")
        
        # Check shape compatibility for matching keys
        shape_mismatches = []
        for key in matching:
            model_shape = model_state[key].shape
            ckpt_shape = cleaned_state_dict[key].shape
            if model_shape != ckpt_shape:
                shape_mismatches.append((key, model_shape, ckpt_shape))
        
        if shape_mismatches:
            print(f"\n      ⚠ Shape mismatches ({len(shape_mismatches)}):")
            for key, m_shape, c_shape in shape_mismatches[:10]:
                print(f"        - {key}: model={m_shape}, ckpt={c_shape}")
        else:
            print(f"\n      ✓ All matching parameters have compatible shapes")
        
        # Try loading
        print()
        print("=" * 60)
        if len(missing_in_ckpt) == 0 and len(shape_mismatches) == 0:
            print("✓ CHECKPOINT IS FULLY COMPATIBLE")
            print("  All model parameters are present with correct shapes.")
        elif len(matching) > len(model_keys) * 0.8 and len(shape_mismatches) == 0:
            print("✓ CHECKPOINT IS MOSTLY COMPATIBLE")
            print(f"  {len(matching)}/{len(model_keys)} parameters match.")
            print("  Can load with strict=False")
        else:
            print("⚠ CHECKPOINT MAY HAVE COMPATIBILITY ISSUES")
            print("  Review the missing/extra parameters above.")
        print("=" * 60)
        
        # Test actual loading
        print()
        print("Attempting to load weights...")
        try:
            model.load_state_dict(cleaned_state_dict, strict=False)
            print("✓ Weights loaded successfully (strict=False)")
            
            # Try strict loading
            try:
                model2 = TCP(config)
                model2.load_state_dict(cleaned_state_dict, strict=True)
                print("✓ Weights loaded successfully (strict=True)")
            except Exception as e:
                print(f"ℹ Strict loading failed (expected if extra/missing keys): {type(e).__name__}")
                
        except Exception as e:
            print(f"✗ Failed to load weights: {e}")
        
        return True
        
    except Exception as e:
        print(f"      ✗ Failed to compare with TCP model: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check TCP checkpoint compatibility')
    parser.add_argument('checkpoint', nargs='?', 
                       default='best_epoch=24-val_loss=0.640.ckpt',
                       help='Path to checkpoint file')
    
    args = parser.parse_args()
    
    check_checkpoint(args.checkpoint)

