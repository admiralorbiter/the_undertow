#!/usr/bin/env python
"""
Pipeline runner script.
Runs the NLP & Analytics pipeline to generate embeddings, clusters, UMAP, and labels.

Usage:
    python tools/run_pipeline.py                    # Run all steps (3-7)
    python tools/run_pipeline.py --step 4           # Run from step 4 onwards
    python tools/run_pipeline.py --step 3 --force    # Force recompute from step 3
    python tools/run_pipeline.py --status            # Show pipeline status
"""
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.pipeline import PipelineRunner
from backend.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Run the NLP & Analytics pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/run_pipeline.py              # Run all steps
  python tools/run_pipeline.py --step 4     # Run from step 4
  python tools/run_pipeline.py --force       # Force recompute everything
  python tools/run_pipeline.py --status     # Check status
        """
    )
    
    parser.add_argument(
        '--step',
        type=int,
        default=3,
        choices=[3, 4, 5, 6, 7, 8, 9, 10],
        help='Starting step number (3-10, default: 3)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recompute even if step already completed'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show pipeline status and exit'
    )
    
    args = parser.parse_args()
    
    # Ensure directories exist
    Config.ensure_directories()
    
    runner = PipelineRunner()
    
    if args.status:
        # Show status
        status = runner.get_pipeline_status()
        print("\n=== Pipeline Status ===\n")
        print(f"Steps completed: {status.get('steps_completed', [])}")
        print(f"Embeddings: {status.get('embeddings_count', 0)}")
        print(f"Similarity edges: {status.get('similarities_count', 0)}")
        print(f"Clusters: {status.get('clusters_count', 0)}")
        print(f"Articles with UMAP coords: {status.get('articles_with_umap', 0)}")
        print(f"Clusters labeled: {status.get('clusters_labeled', 0)}")
        print(f"Storylines: {status.get('storylines_count', 0)}")
        print(f"Alerts: {status.get('alerts_count', 0)}")
        print(f"FAISS index exists: {status.get('has_faiss_index', False)}")
        return
    
    # Run pipeline
    print(f"\n=== Running Pipeline (starting from step {args.step}) ===\n")
    
    if args.force:
        print("[FORCE] Force recompute enabled - will recompute even if already completed\n")
    
    try:
        results = runner.run_full_pipeline(
            start_from_step=args.step,
            force_recompute=args.force
        )
        
        print("\n=== Pipeline Results ===\n")
        
        for step_key, result in results.items():
            status = result.get('status', 'unknown')
            step_num = step_key.replace('step_', '')
            
            if status == 'completed':
                print(f"[OK] Step {step_num}: Completed")
                
                # Show step-specific stats
                if 'processed' in result:
                    print(f"   Processed: {result['processed']}")
                if 'edges_created' in result:
                    print(f"   Edges created: {result['edges_created']}")
                if 'clusters_created' in result:
                    print(f"   Clusters: {result['clusters_created']}")
                    print(f"   Articles clustered: {result.get('articles_clustered', 0)}")
                    print(f"   Noise points: {result.get('noise', 0)}")
                if 'points_projected' in result:
                    print(f"   Points projected: {result['points_projected']}")
                if 'clusters_labeled' in result:
                    print(f"   Clusters labeled: {result['clusters_labeled']}")
                if 'storylines_created' in result:
                    print(f"   Storylines created: {result['storylines_created']}")
                    print(f"   Articles grouped: {result.get('articles_grouped', 0)}")
                if 'alerts_created' in result:
                    print(f"   Alerts created: {result['alerts_created']}")
                    print(f"   Surges: {result.get('surges', 0)}")
                    print(f"   Reactivations: {result.get('reactivations', 0)}")
                    print(f"   New actors: {result.get('new_actors', 0)}")
                    
            elif status == 'skipped':
                print(f"[SKIP] Step {step_num}: Skipped (already completed)")
            elif status == 'error':
                print(f"[ERROR] Step {step_num}: Error - {result.get('error', 'Unknown error')}")
            elif status == 'not_implemented':
                print(f"[P2] Step {step_num}: Not implemented (P2 feature)")
            else:
                print(f"[WARNING] Step {step_num}: Status: {status}")
            
            print()
        
        # Show final status
        final_status = runner.get_pipeline_status()
        print("=== Final Status ===\n")
        print(f"Embeddings: {final_status.get('embeddings_count', 0)}")
        print(f"Similarity edges: {final_status.get('similarities_count', 0)}")
        print(f"Clusters: {final_status.get('clusters_count', 0)}")
        print(f"Articles with UMAP: {final_status.get('articles_with_umap', 0)}")
        print(f"Clusters labeled: {final_status.get('clusters_labeled', 0)}")
        print(f"Storylines: {final_status.get('storylines_count', 0)}")
        print(f"Alerts: {final_status.get('alerts_count', 0)}")
        
        print("\n[SUCCESS] Pipeline execution complete!\n")
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Pipeline interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n[ERROR] Pipeline failed: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()

