import pandas as pd
from tqdm import tqdm
import os
import re
import pyteomics
from pyteomics import mgf
import matplotlib.pyplot as plt
import numpy as np
import re
from typing import Dict, Iterable, List, Tuple
from spectrum_utils.utils import mass_diff
import sys
import re
from lxml import etree
import xml.etree.ElementTree as ET
from sklearn.metrics import auc
import matplotlib.pyplot as plt

from calculate_criteria import aa_match_batch

def modify_de_novo_result_with_filter_out_df(result_df, mod_dict):
  sequences = result_df['sequence'].fillna("").astype(str)
  mass_delta_pattern = r'\+\d+\.\d+|\+\d+|\-\d+\.\d+|\-\d+'
  total_matches = int(sequences.str.count(mass_delta_pattern).sum())

  mod_tokens = set()
  for mod in mod_dict:
    mod_tokens.update(re.findall(mass_delta_pattern, mod))

  if mod_tokens:
    affected_pattern = "|".join(re.escape(token) for token in sorted(mod_tokens, key=len, reverse=True))
    mask = sequences.str.contains(affected_pattern, regex=True, na=False)
    num_replaced = int(sum(sequences.str.count(re.escape(token)).sum() for token in mod_tokens))
  else:
    mask = pd.Series(False, index=result_df.index)
    num_replaced = 0

  affected_df = result_df[mask]
  unaffected_df = result_df[~mask]
  num_affected = int(mask.sum())

  print(f"Num replaced: {num_replaced}")
  print(f"Percent replaced: {num_replaced/total_matches*100:.2f}%" if total_matches else "Percent replaced: 0.00%")
  print(f"Percent affected: {num_affected/len(result_df)*100:.2f}%" if len(result_df) else "Percent affected: 0.00%")

  return unaffected_df, affected_df

############### InstaNovo output processing ###############

def instanovo_filter_out_unspecified_mods(instanovo_df, unimod_dict, toolname):
    seq_pred_col = f'{toolname}_seq'
    total_rows = len(instanovo_df)  # Save initial row count for stats

    # Step 1: Apply known modifications, ensuring values are treated as strings
    instanovo_df[seq_pred_col] = instanovo_df[seq_pred_col].fillna("").astype(str)
    for original, modified in unimod_dict.items():
        instanovo_df[seq_pred_col] = instanovo_df[seq_pred_col].str.replace(original, modified, regex=False)
    instanovo_df[seq_pred_col] = instanovo_df[seq_pred_col].astype(object)

    # Step 2: Identify rows that still contain unknown UNIMOD modifications.
    # Note: Removing .any() so that we get a boolean mask per row.
    unspecified_mod_mask = instanovo_df[seq_pred_col].str.contains(r'\[UNIMOD:\d+\]', regex=True)
    # Ensure it is a valid boolean Series.
    unspecified_mod_mask = unspecified_mod_mask.fillna(False).astype(bool)
    
    removed_count = unspecified_mod_mask.sum()

    # Step 3: Filter out rows where the mask is True.
    instanovo_df = instanovo_df[~unspecified_mod_mask].reset_index(drop=True)
    
    # Step 4: Report removal statistics.
    removed_fraction = (removed_count / total_rows) * 100
    print(f"Removed {removed_count} rows with unknown UNIMOD modifications "
          f"({removed_fraction:.2f}% of total).")

    return instanovo_df

############### PepNovo+ output processing ###############

def read_pepnovo_predictions(file_path):
    """
    Reads a file containing peptide predictions and returns a DataFrame with corrections.
    """
    data_blocks = []
    current_title = ""

    with open(file_path, 'r') as file:
        for line in file:  # Reading line by line is more efficient than readlines() for large files
            if line.startswith(">>") and "File:" in line:  # Adjusted to correctly identify title lines
                current_title = extract_correct_title_part(line.strip())
            elif line[0].isdigit():
                parts = line.strip().split()
                if len(parts) > 7:  # Ensuring that the line has enough parts to parse
                    row_data = {
                        'title': current_title,
                        'Index': parts[0],
                        'RnkScr': parts[1],
                        'PnvScr': parts[2],
                        'N-Gap': parts[3],
                        'C-Gap': parts[4],
                        '[M+H]': parts[5],
                        'Charge': parts[6],
                        'sequence': ' '.join(parts[7:])
                    }
                    data_blocks.append(row_data)

    df = pd.DataFrame(data_blocks)
    return df

def extract_correct_title_part(line):
    """
    Extracts the title and scan number from a line, formatted correctly.
    The target output is up to and including the scan number, for example:
    'E_Aurora25_huMu-deepC18_dia_400ng-frac6_A3164-6.60060'
    """
    # Split the line into parts to isolate the segment of interest
    parts = line.split()
    # The correct segment of interest is now parts[3]
    segment_of_interest = parts[3]

    # Split by "." and keep the first two parts
    split_segment = segment_of_interest.split('.')
    if len(split_segment) > 1:
        # Join the first two segments with a "." to reconstruct the desired part
        desired_title_part = '.'.join(split_segment[:2])
    else:
        # If there's no period or only one, use the segment as it is
        desired_title_part = segment_of_interest

    return desired_title_part

############### Benchmark mgf processing ###############

def parse_benchmark_mgf(ground_truth_file_path):
    mgf_file = mgf.IndexedMGF(str(ground_truth_file_path))
    titles = []  # List to store titles for DataFrame
    seqs = []

    # Iterate through each spectrum in the MGF file
    for spectrum in tqdm(mgf_file):
        title = spectrum['params']['title']
        seq = spectrum['params']['seq']
        # Split the title at periods and reconstruct it without the last part
        parts = title.split('.')
        # Ensure there are enough parts to avoid IndexError
        if len(parts) >= 3:
            # Reconstruct title without the last section after the last period
            processed_title = '.'.join(parts[:-3])
        else:
            processed_title = title  # Use the original title if it doesn't match the expected format

        # Append the processed title to the titles list
        titles.append(processed_title)
        seqs.append(seq)

    # Convert the titles list to a DataFrame
    df = pd.DataFrame({'title': titles, 'groundtruth_seq': seqs})

    # Add an explicit 'index' column based on the DataFrame's inherent index
    df['pos_index'] = range(len(df))  # Rename to avoid conflic

    return df

############### ContraNovo output processing ###############

def parse_file_to_dataframe(file_path):
    data = []  # Prepare an empty list to hold dictionaries

    current_title = None
    current_sequence = None
    current_scores = []

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if "File:" in line:
                if current_title:  # If there's a title already found, this means we're at a new section
                    avg_score = sum(current_scores) / len(current_scores) if current_scores else 0
                    data.append({
                        "title": current_title,
                        "sequence": current_sequence,
                        "aa_scores": current_scores,
                        "search_engine_score[1]": avg_score
                    })
                title_parts = line.split()[0].split('.')  # Splitting the title at spaces and then at periods
                # Reconstructing the title to exclude the last two segments
                current_title = '.'.join(title_parts[:-2])
                current_sequence = line.split(':')[-1].strip()  # Extracting sequence after the last colon
                current_scores = []
            elif line.startswith("Position"):
                _, score = line.split(':')
                current_scores.append(float(score.strip()))

    if current_title:  # Add the last section
        avg_score = sum(current_scores) / len(current_scores) if current_scores else 0
        data.append({
            "title": current_title,
            "sequence": current_sequence,
            "aa_scores": current_scores,
            "search_engine_score[1]": avg_score
        })

    df = pd.DataFrame(data)  # Convert the list of dictionaries to a DataFrame
    return df

############### MSGF+ output processing ###############

def parse_mgfsplus_mods(result_df, mod_dict):
    result_df['peptide_seq'] = result_df['peptide_seq'].fillna("").astype(str)
    for original, modified in mod_dict.items():
        result_df['peptide_seq'] = result_df['peptide_seq'].str.replace(original, modified, regex=False)

    # Adjust this line to extract the sequence between the first and last points
    result_df['peptide_seq'] = result_df['peptide_seq'].str.replace(r'^[^.]*\.(.*)\.[^.]*$', r'\1', regex=True)
    result_df['peptide_seq'] = result_df['peptide_seq'].astype(object)

    return result_df

############### Metric calculation ###############

def calculate_peptide_precision_coverage(psm_sequences, aa_dict, tool_name):
    # Sort the PSMs by decreasing prediction score.
    psm_sequences_sorted = psm_sequences.sort_values(f'{tool_name}_score', ascending=False)

    # Calculate matches and precision/coverage.
    aa_matches_batch = aa_match_batch(psm_sequences_sorted["groundtruth_seq"], psm_sequences_sorted[f'{tool_name}_seq'], aa_dict)
    peptide_matches = np.asarray([aa_match[1] for aa_match in aa_matches_batch[0]])
    precision = np.cumsum(peptide_matches) / np.arange(1, len(peptide_matches) + 1)
    coverage = np.arange(1, len(peptide_matches) + 1) / len(peptide_matches)

    # Get the sorted scores
    scores = psm_sequences_sorted[f'{tool_name}_score'].values

    return coverage, precision, scores

def calculate_aa_precision_coverage(psm_sequences, aa_dict, tool_name):
    # Sort the PSMs by decreasing prediction score.
    psm_sequences_sorted = psm_sequences.sort_values(f'{tool_name}_score', ascending=False)

    # Prepare an array to hold the scores, repeated by the length of each peptide sequence
    scores_repeated = []
    for _, row in psm_sequences_sorted.iterrows():
        aa_length = len(row[f'{tool_name}_seq'])  # Assuming 'sequence' holds the peptide sequence
        scores_repeated.extend([row[f'{tool_name}_score']] * aa_length)

    # Calculate matches and precision/coverage.
    aa_matches_batch = aa_match_batch(psm_sequences_sorted["groundtruth_seq"], psm_sequences_sorted[f'{tool_name}_seq'], aa_dict)
    aa_matches = np.concatenate([aa_match[0] for aa_match in aa_matches_batch[0]])  # Flatten boolean matches for AAs
    precision = np.cumsum(aa_matches) / np.arange(1, len(aa_matches) + 1)
    coverage = np.arange(1, len(aa_matches) + 1) / len(aa_matches)

    # Convert the list of scores to a numpy array and ensure it's the same length as aa_matches
    scores = np.array(scores_repeated[:len(aa_matches)])

    return coverage, precision, scores
