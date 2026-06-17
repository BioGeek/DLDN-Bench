import pandas as pd
import argparse

from constants import modification_dict, novor_modification_dict, pepnovoplus_result_mod_dict, unimod_dict
from utils import parse_benchmark_mgf, parse_mgfsplus_mods, read_pepnovo_predictions, modify_de_novo_result_with_filter_out_df, parse_file_to_dataframe, instanovo_filter_out_unspecified_mods

def create_result_csv(ground_truth_file_path,
                      msgfplus_result_file_path,
                      pepnovoplus_result_file_path,
                      novor_result_file_path,
                      casanovo_result_file_path,
                      pi_helixnovo_result_file_path,
                      contranovo_result_file_path_list,
                      instanovo_result_file_path,
                      save_path=None,
                      additional_result_file_path=None,
                      additional_result_name=None,
                    ):
    

    ####################### groundtruth_seqs #######################

    print('parse groundtruth MGF')

    df = parse_benchmark_mgf(ground_truth_file_path)

    ####################### msgfplus #######################

    print('parse MSGF+ prediction file')

    msgfplus_result_df = pd.read_parquet(msgfplus_result_file_path)

    msgfplus_result_df['scannr'] = msgfplus_result_df['psm_id'].apply(lambda x: x.split('_')[-3] if len(x.split('_')) >= 5 else None)

    msgfplus_result_df['pos_index'] = msgfplus_result_df['psm_id'].apply(lambda x: int(x.split('_')[-5]) - 1 if len(x.split('_')) >= 5 else None)

    filter_msgfplus = False

    # filter
    if filter_msgfplus:
        
        msgfplus_result_df = msgfplus_result_df[msgfplus_result_df['q_value']<0.01]

    # parse modifications
    msgfplus_result_df = parse_mgfsplus_mods(msgfplus_result_df, unimod_dict)

    msgfplus_result_df.rename(columns={'peptide_seq': 'msgfplus_percolator_seq', 'svm_score' : 'msgfplus_percolator_score'}, inplace=True)

    # extract relevant cols and merge

    msgfplus_merge_df = msgfplus_result_df[["pos_index", "msgfplus_percolator_seq", "msgfplus_percolator_score"]]

    merged_df = df.merge(msgfplus_merge_df, on='pos_index', how='inner')

    ####################### pepnovoplus #######################

    print('parse PepNovo+ prediction file')

    pepnovoplus_df = read_pepnovo_predictions(pepnovoplus_result_file_path)     

    for old, new in pepnovoplus_result_mod_dict.items():

      pepnovoplus_df['sequence'] = pepnovoplus_df['sequence'].str.replace(old, new, regex=False)

    pepnovoplus_df.rename(columns={'sequence':'pepnovoplus_seq','RnkScr': 'pepnovoplus_score'}, inplace=True)

    pepnovoplus_df['pepnovoplus_score'] = pepnovoplus_df['pepnovoplus_score'].astype(float)

    # extract relevant cols and merge

    pepnovoplus_df = pepnovoplus_df[['title','pepnovoplus_seq','pepnovoplus_score']]

    merged_df = merged_df.merge(pepnovoplus_df, how='inner', on='title')

    ####################### novor #######################

    print('parse Novor prediction file')
    
    # Open the file and find where the header starts
    header_line = None
    with open(novor_result_file_path, 'r') as file:
        for i, line in enumerate(file):
            if line.startswith('# id, scanNum, RT, mz(data), z, pepMass(denovo), err(data-denovo), ppm(1e6*err/(mz*z)), score, peptide, aaScore,'):
                header_line = i
                break

    # Check if header_line was found
    if header_line is not None:
        # Now read the data from the next line after the header
        novor_result_df = pd.read_csv(novor_result_file_path, skiprows=header_line + 1, header=None)
        # Set the column names manually
        novor_result_df.columns = ['id', 'scanNum', 'RT', 'mz(data)', 'z', 'pepMass(denovo)', 'err(data-denovo)', 'ppm(1e6*err/(mz*z))', 'score', 'peptide', 'aaScore']
    else:
        print("Header line not found.")

    for index, row in novor_result_df.iterrows():
        peptide = row['peptide']

        # Apply modifications directly within this loop
        for mod, value in novor_modification_dict.items():
            peptide = peptide.replace(mod, value)

        # Strip leading and trailing whitespaces
        peptide = peptide.strip()

        # For demonstration, just updating the peptide back in the DataFrame
        novor_result_df.at[index, 'peptide'] = peptide

    novor_result_df['pos_index'] = range(len(novor_result_df))

    novor_result_df.rename(columns={'peptide': 'novor_seq', 'score':'novor_score'}, inplace=True)

    # extract relevant cols and merge

    novor_result_df = novor_result_df[['pos_index','novor_seq', 'novor_score']]

    merged_df = merged_df.merge(novor_result_df, how='inner', on='pos_index')

    ####################### casanovo #######################

    print('parse CasaNovo prediction file')

    with open(casanovo_result_file_path) as f_in:
        for skiprows, line in enumerate(f_in):
            if line.startswith("PSH"):
                break

    casanovo_result_df = pd.read_csv(casanovo_result_file_path, skiprows=skiprows, sep="\t")
    casanovo_result_df['pos_index'] = casanovo_result_df['spectra_ref'].str.extract(r'index=(\d+)').astype(int)
    casanovo_result_df, _ = modify_de_novo_result_with_filter_out_df(casanovo_result_df, modification_dict)

    casanovo_result_df.rename(columns={'sequence':'casanovo_seq','search_engine_score[1]':'casanovo_score'}, inplace=True)

    # extract relevant cols and merge

    casanovo_result_df = casanovo_result_df[['pos_index', 'casanovo_seq', 'casanovo_score']]

    merged_df = merged_df.merge(casanovo_result_df, how='inner', on='pos_index')

    ####################### pi-helixnovo #######################

    print('parse Pi-HelixNovo prediction file')

    pi_helixnovo_result_df = pd.read_csv(pi_helixnovo_result_file_path, sep='\t', names=['title','sequence', 'p'] )

    pi_helixnovo_result_df['pos_index'] = range(len(pi_helixnovo_result_df))

    pi_helixnovo_result_df, unknown_ptm_df = modify_de_novo_result_with_filter_out_df(pi_helixnovo_result_df, modification_dict)

    pi_helixnovo_result_df.rename(columns={'sequence':'pi_helixnovo_seq','p': 'pi_helixnovo_score'}, inplace=True)

    # extract relevant cols and merge

    pi_helixnovo_result_df = pi_helixnovo_result_df[['pos_index','pi_helixnovo_seq','pi_helixnovo_score']]

    merged_df = merged_df.merge(pi_helixnovo_result_df, how='inner', on='pos_index')

    ####################### contranovo #######################

    print('parse ContraNovo prediction file')

    contranovo_result_df = pd.DataFrame()

    for contranovo_result_file_path in contranovo_result_file_path_list:

        curr_contranovo_result_df = parse_file_to_dataframe(contranovo_result_file_path)

        contranovo_result_df = pd.concat([contranovo_result_df, curr_contranovo_result_df], ignore_index=True)


    ## only keep prediction with highest score per title

    # Get the index of the row with the maximum search_engine_score[1] for each title

    idx = contranovo_result_df.groupby('title')['search_engine_score[1]'].idxmax()

    # Use the index to select the corresponding rows

    contranovo_result_df = contranovo_result_df.loc[idx].reset_index(drop=True)

    contranovo_result_df, _ = modify_de_novo_result_with_filter_out_df(contranovo_result_df, modification_dict)

    contranovo_result_df.rename(columns={'sequence':'contranovo_seq','search_engine_score[1]':'contranovo_score'}, inplace=True)

    # extract relevant cols and merge

    contranovo_result_df = contranovo_result_df[['title', 'contranovo_seq','contranovo_score']]

    merged_df = merged_df.merge(contranovo_result_df, how='inner', on='title')

    ####################### instanovo & instanovoplus #######################

    print('parse InstaNovo prediction file')

    instanovo_result_df = pd.read_csv(instanovo_result_file_path)

    instanovo_result_df['pos_index'] = range(len(instanovo_result_df))

    instanovo_result_df.rename(columns={'transformer_predictions':'instanovo_seq', 'transformer_log_probabilities':'instanovo_score', 
                                'diffusion_predictions':'instanovoplus_seq', 'diffusion_log_probabilities':'instanovoplus_score'}, inplace=True)

    instanovo_df = instanovo_filter_out_unspecified_mods(instanovo_result_df, unimod_dict, 'instanovo') # parse mods to expected format + filter out predictions with unspecified mods

    instanovoplus_df = instanovo_filter_out_unspecified_mods(instanovo_result_df, unimod_dict, 'instanovoplus') # parse mods to expected format + filter out predictions with unspecified mods

    # extract relevant cols and merge
    
    instanovo_df = instanovo_df[['pos_index', 'instanovo_seq', 'instanovo_score']]

    merged_df = merged_df.merge(instanovo_df, how='inner', on='pos_index')

    instanovoplus_df = instanovoplus_df[['pos_index', 'instanovoplus_seq', 'instanovoplus_score']]

    merged_df = merged_df.merge(instanovoplus_df, how='inner', on='pos_index')

    ####################### additional result file #######################

    if additional_result_file_path and additional_result_name:
        
        print(f'parse {additional_result_name} prediction file')

        additional_result_df = pd.read_csv(additional_result_file_path)

        if 'scan_number' in additional_result_df.columns:
            additional_result_df['pos_index'] = additional_result_df['scan_number'].astype(int)
        else:
            additional_result_df['pos_index'] = range(len(additional_result_df))

        # Use the same format as InstaNovo - expecting 'predictions' and 'probabilities' columns
        if 'predictions' in additional_result_df.columns:
            additional_score_candidates = ['scores', 'log_probs', 'log_probabilities', 'score']
            additional_score_col = next(
                (col for col in additional_score_candidates if col in additional_result_df.columns),
                None,
            )
            if additional_score_col is None:
                raise ValueError(
                    f"Could not find a score column for {additional_result_name}. "
                    f"Columns: {additional_result_df.columns.tolist()}"
                )
            additional_result_df.rename(columns={'predictions': f'{additional_result_name}_seq',
                                               additional_score_col: f'{additional_result_name}_score'}, inplace=True)
        else:
            # Alternative: look for common column names and rename them
            # This assumes the file has 'sequence' and 'score' columns or similar
            if 'sequence' in additional_result_df.columns:
                additional_result_df.rename(columns={'sequence': f'{additional_result_name}_seq'}, inplace=True)
            if 'score' in additional_result_df.columns:
                additional_result_df.rename(columns={'score': f'{additional_result_name}_score'}, inplace=True)

        # Filter out unspecified mods using the same function as InstaNovo
        additional_result_df = instanovo_filter_out_unspecified_mods(additional_result_df, unimod_dict, additional_result_name)

        # extract relevant cols and merge
        additional_result_df = additional_result_df[['pos_index', f'{additional_result_name}_seq', f'{additional_result_name}_score']]

        merged_df = merged_df.merge(additional_result_df, how='inner', on='pos_index')

    #######################################################################################################################################

    merged_df.to_csv(save_path)

    print(f'result csv file saved on {save_path}')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Align prediction files from different tools")

    parser.add_argument('-gt', '--ground_truth_file_path', required=True, 
                        help='Path to benchmark MGF with annotated sequences')

    parser.add_argument('-msgfplus', '--msgfplus_pred_file_path', required=True, 
                        help='Path to MSGF+ prediction file')

    parser.add_argument('-pepnovoplus', '--pepnovoplus_pred_file_path', required=True, 
                        help='Path to PepNovo+ prediction file')

    parser.add_argument('-novor', '--novor_pred_file_path', required=True, 
                        help='Path to Novor prediction file')

    parser.add_argument('-casanovo', '--casanovo_pred_file_path', required=True, 
                        help='Path to CasaNovo prediction file')

    parser.add_argument('-pi_helixnovo', '--pi_helixnovo_pred_file_path', required=True, 
                        help='Path to π-HelixNovo prediction file')

    parser.add_argument('-contranovo', '--contranovo_pred_file_path', required=True, 
                        nargs='+', help='Path(s) to ContraNovo prediction file(s)')

    parser.add_argument('-instanovo', '--instanovo_pred_file_path', required=True, 
                        help='Path to InstaNovo prediction file')

    parser.add_argument('-save_path', required=False, default='benchmark_predictions.csv',
                        help='Path to save the csv file')
    
    parser.add_argument('-additional_file', '--additional_result_file_path', required=False, 
                        help='Path to additional result file (InstaNovo format)')

    parser.add_argument('-additional_name', '--additional_result_name', required=False, 
                        help='Name for the additional result file (used as column prefix)')

    args = parser.parse_args()

    create_result_csv(ground_truth_file_path=args.ground_truth_file_path,
                        msgfplus_result_file_path=args.msgfplus_pred_file_path,
                        pepnovoplus_result_file_path=args.pepnovoplus_pred_file_path,
                        novor_result_file_path=args.novor_pred_file_path,
                        casanovo_result_file_path=args.casanovo_pred_file_path,
                        pi_helixnovo_result_file_path=args.pi_helixnovo_pred_file_path,
                        contranovo_result_file_path_list=args.contranovo_pred_file_path,
                        instanovo_result_file_path=args.instanovo_pred_file_path,
                        save_path=args.save_path,
                        additional_result_file_path=args.additional_result_file_path,
                        additional_result_name=args.additional_result_name)
