import argparse
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for CLI
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm
from sklearn.metrics import auc

from constants import aa_dict, tool_name_plot_name_dict
from utils import calculate_peptide_precision_coverage, calculate_aa_precision_coverage

default_tool_display_names = {
    "instanovo_v1_1": "InstaNovo v1.1 Zenodo transformer",
    "instanovo_v1_2": "InstaNovo v1.2.0 transformer",
}

tool_plot_color_dict = {
    # Match the published Figure 1 Matplotlib tab10 colours.
    "msgfplus_percolator": "#1f77b4",
    "contranovo": "#ff7f0e",
    "instanovo": "#2ca02c",
    "instanovo_v1_1": "#2ca02c",
    "casanovo": "#d62728",
    "pi_helixnovo": "#9467bd",
    "novor": "#8c564b",
    "pepnovoplus": "#e377c2",
    # New tool/version, intentionally distinct from published InstaNovo v1.1.
    "instanovo_v1_2": "#17becf",
}

def get_tool_names_from_columns(df):
    """Extract tool names from columns that follow {toolname}_seq and {toolname}_score pattern"""
    tool_names = set()
    
    for col in df.columns:
        # Look for columns ending with '_seq'
        if col.endswith('_seq') and col != 'groundtruth_seq':
            tool_name = col[:-4]  # Remove '_seq' suffix
            # Check if corresponding '_score' column exists
            if f'{tool_name}_score' in df.columns:
                tool_names.add(tool_name)
    
    return list(tool_names)

def plot_precision_coverage_curves(result_df, tool_name_dict, benchmark_dataset_name=None, save_plot_path=None, save_tables_path=None):

    """
    Generate precision-coverage curves for peptide sequencing tools.
    
    Args:
        result_df: DataFrame with ground truth and predictions
        tool_name_dict: Dictionary mapping tool keys to display names
        benchmark_dataset_name: Name for output files
        save_plot_path: Directory to save plots (required for CLI)
        save_tables_path: Directory to save CSV tables
    
    Returns:
        dict: Summary statistics including AUC scores
    """
  
    # drop rows with NaN predictions that can occur in InstaNovo+
  
    if 'instanovoplus' in tool_name_dict.keys():
         
        result_df = result_df[result_df["instanovoplus_seq"].notna() & (result_df["instanovoplus_seq"] != "")]


    # To store combined curves in overall DataFrames
    peptide_df = pd.DataFrame()
    aa_df = pd.DataFrame()

    # Initialize lists for plotting and storing scores
    all_peptide_coverages = []
    all_peptide_precisions = []
    all_peptide_scores = []
    all_aa_coverages = []
    all_aa_precisions = []
    all_aa_scores = []
    peptide_auc_scores = []
    aa_auc_scores = []

  

    for tool_name in tqdm(tool_name_dict.keys(), desc="Processing tools"):

        print(f'processing: {tool_name}')
        
        tool_df = result_df[['groundtruth_seq', f'{tool_name}_seq', f'{tool_name}_score']]
        
        # Calculate peptide precision, coverage, and scores
        peptide_coverage, peptide_precision, peptide_scores = calculate_peptide_precision_coverage(tool_df, aa_dict, tool_name)
        all_peptide_coverages.append(peptide_coverage)
        all_peptide_precisions.append(peptide_precision)
        all_peptide_scores.append(peptide_scores)
        peptide_auc_score = auc(peptide_coverage, peptide_precision)
        peptide_auc_scores.append(peptide_auc_score)

        # Calculate AA precision, coverage, and scores
        aa_coverage, aa_precision, aa_scores = calculate_aa_precision_coverage(tool_df, aa_dict, tool_name)
        all_aa_coverages.append(aa_coverage)
        all_aa_precisions.append(aa_precision)
        all_aa_scores.append(aa_scores)
        aa_auc_score = auc(aa_coverage, aa_precision)
        aa_auc_scores.append(aa_auc_score)

        # Add these arrays to the overall peptide_df. Each array is wrapped in a pd.Series.
        # pd.Series automatically handles varying lengths by filling missing entries with NaN.
        peptide_df[f"{tool_name}_peptide_precision"] = pd.Series(peptide_precision)
        peptide_df[f"{tool_name}_peptide_coverage"] = pd.Series(peptide_coverage)

        aa_df[f"{tool_name}_aa_precision"] = pd.Series(aa_precision)
        aa_df[f"{tool_name}_aa_coverage"] = pd.Series(aa_coverage)

    print(f'Based on {len(result_df)} peptide-spectrum matches')

    # Plot peptide precision vs. coverage with AUC scores
    plt.figure(figsize=(10, 6))
    peptide_plot_data = zip(
        all_peptide_coverages,
        all_peptide_precisions,
        all_peptide_scores,
        tool_name_dict.keys(),
        tool_name_dict.values(),
        peptide_auc_scores,
    )
    for cov, prec, sc, tool_key, tool_name, auc_score in sorted(peptide_plot_data, key=lambda x: x[5], reverse=True):
            plt.plot(
                cov,
                prec,
                label=f"{tool_name} (AUC = {auc_score:.3f})",
                linewidth=3.5,
                color=tool_plot_color_dict.get(tool_key),
            )

    plt.xlabel("Coverage", fontsize=14)
    plt.ylabel("Precision", fontsize=14)
    plt.title(f"Peptide Precision vs. Coverage (Benchmark Dataset: {benchmark_dataset_name})")
    plt.xlim(0.01, 1.0)  # Start at 0.01 to clip initial artifacts
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', ncol=1, fontsize=11)  # Place legend outside
    plt.grid(True)
    plt.tight_layout()  # Adjust layout to fit everything

    # Save peptide plot if save_plot_path is provided
    if save_plot_path is not None:
            peptide_plot_path = f"{save_plot_path}/{benchmark_dataset_name}_peptide_precision_coverage.png"
            plt.savefig(peptide_plot_path, dpi=600, bbox_inches='tight')
            print(f"Peptide plot saved to {peptide_plot_path}")

    plt.close()  # Close figure to free memory

    # Plot aa precision vs. coverage with AUC scores
    plt.figure(figsize=(10, 6))
    aa_plot_data = zip(
        all_aa_coverages,
        all_aa_precisions,
        all_aa_scores,
        tool_name_dict.keys(),
        tool_name_dict.values(),
        aa_auc_scores,
    )
    for cov, prec, sc, tool_key, tool_name, auc_score in sorted(aa_plot_data, key=lambda x: x[5], reverse=True):
            plt.plot(
                cov,
                prec,
                label=f"{tool_name} (AUC = {auc_score:.3f})",
                linewidth=3.5,
                color=tool_plot_color_dict.get(tool_key),
            )
            

    plt.xlabel("Coverage", fontsize=14)
    plt.ylabel("Precision", fontsize=14)
    plt.title(f"AA Precision vs. Coverage (Benchmark Dataset: {benchmark_dataset_name})")
    plt.xlim(0.01, 1.0)  # Start at 0.01 to clip initial artifacts
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', ncol=1, fontsize=11)  # Place legend outside
    plt.grid(True)
    plt.tight_layout()  # Adjust layout to fit everything

    # Save AA plot if save_plot_path is provided
    if save_plot_path is not None:
            aa_plot_path = f"{save_plot_path}/{benchmark_dataset_name}_aminoacid_precision_coverage.png"
            plt.savefig(aa_plot_path, dpi=600, bbox_inches='tight')
            print(f"AA plot saved to {aa_plot_path}")

    plt.close()  # Close figure to free memory
    
    if save_tables_path is not None:

        # Save the overall DataFrames to CSV files.

        peptide_df.to_csv(f'{save_tables_path}/{benchmark_dataset_name}_peptide_precision_coverage.csv', index=False)
        aa_df.to_csv(f'{save_tables_path}/{benchmark_dataset_name}_aminoacid_precision_coverage.csv', index=False)

        print(f'Table files saved: {save_tables_path}/{benchmark_dataset_name}_peptide_precision_coverage.csv and{save_tables_path}/{benchmark_dataset_name}_aminoacid_precision_coverage.csv')
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze precision and coverage of peptide sequencing tools")
    
    parser.add_argument('-i', '--input', required=True, 
                       help='Input CSV file with results')
    parser.add_argument('-o', '--output', required=True,
                       help='Output directory for plots')
    parser.add_argument('-d', '--dataset', required=True,
                       help='Dataset name for output files')
    parser.add_argument('--tables',
                       help='Directory to save CSV tables')
    
    args = parser.parse_args()
    
    # Load data
    result_df = pd.read_csv(args.input)
    
    # Get all available tools dynamically
    available_tools = get_tool_names_from_columns(result_df)

    # Filter out instanovoplus because not recent version was available
    excluded_tools = ['instanovoplus']  # Add any other tools you want to exclude
    available_tools = [tool for tool in available_tools if tool not in excluded_tools]
    print(f"Found tools: {available_tools}")

    # Build a plot-name dictionary for only the tools present in the input file.
    plot_tool_name_dict = {}
    for tool in available_tools:
        if tool not in tool_name_plot_name_dict:
            # Use the tool name as the plot name (or customize as needed)
            tool_name_plot_name_dict[tool] = default_tool_display_names.get(tool, tool)
            print(f"Added new tool: {tool}")
        plot_tool_name_dict[tool] = tool_name_plot_name_dict[tool]

    print(f"Final tool dictionary: {plot_tool_name_dict}")
    
    # Run analysis
    plot_precision_coverage_curves(
        result_df=result_df,
        tool_name_dict=plot_tool_name_dict,
        benchmark_dataset_name=args.dataset,
        save_plot_path=args.output,
        save_tables_path=args.tables
    )
