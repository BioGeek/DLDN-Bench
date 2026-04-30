# Benchmarking & Evaluation of Deep Learning - based De Novo Peptide Sequencing Models

## General process

1. Get the Evaluation Datasets (Benchmark MGF files) and the prediction files from the models which are uploaded on Zenodo: https://doi.org/10.5281/zenodo.19627459 and apply your new De Novo Model to the Evaluation Datasets (Benchmark Datasets) to get predictions

2. Clone this repo to apply the evaluation to see how your new model performs with respect to current state-of-the-art models on the benchmark datasets
    
    - 2.1. Your predictions need to have a specific format:

        - A csv file with at least the following columns:

        | predictions   | scores                       | 
        |---------------|------------------------------|
        | SEQ1          | Score1                       | 
        | SEQ2          | Score2                       |
        | SEQ3          | Score3                       |
        | ...           | ...                          | 

        - the predictions column should contain the predicted sequence and the scores should be the models confidence score or assigned probabilities
        - Note on modifications: If your predictions contain modifications that are not supported by our evaluation pipeline or have a different format, please edit the dictionaries in "constants.py" accordingly
        - Note on Indexing: The evaluation uses the positional index, so the order should be the same in your provided prediction file, e.g. entry 7 should contain the prediction for spectrum 7 in the benchmark MGF. If the model that you want to test shuffles the order and uses some identifier instead (e.g. the spectrum title), you need to map this to the correct positional order again such that it aligns with the order of the original benchmark file
     
3. Run `create_result_csv.py`, which takes your predictions along with predictions from the state-of-the-art models you want to score against, preprocesses them and aligns them.

   - Provide the prediction files from the models to the corresponding command-line arguments.
   - Also provide the prediction file of your model via `-additional_file` and give it a name via `-additional_name`.

   Your command should look like this:

```bash
   python create_result_csv.py \
     -gt /path/to/PXD006882_benchmark_dataset.mgf \
     -msgfplus /path/to/PXD006882_benchmark_dataset_msgfplus_pred.parquet \
     -pepnovoplus /path/to/PXD006882_benchmark_dataset_pepnovoplus_pred.txt \
     -novor /path/to/PXD006882_benchmark_dataset_novor_pred.csv \
     -casanovo /path/to/PXD006882_benchmark_dataset_casanovo_pred.mztab \
     -pi_helixnovo /path/to/PXD006882_benchmark_dataset_pi_helixnovo_pred.txt \
     -contranovo /path/to/PXD006882_benchmark_dataset_contranovo_pred.txt \
     -instanovo /path/to/PXD006882_benchmark_dataset_instanovo_pred.csv \
     -save_path /path/to/PXD006882_benchmark_predictions.csv \
     -additional_file /path/to/new_model_predictions.csv \
     -additional_name "new_model"
```

4. Run `calc_and_plot_precision_coverage.py` on the aligned predictions, which calculates the evaluation criteria and generates precision-coverage plots at both the peptide and amino acid level, along with the AUC score.

   Your command should look like this:

```bash
   python calc_and_plot_precision_coverage.py \
     --input /path/to/PXD006882_benchmark_predictions.csv \
     --output /path/to/results \
     --dataset "PXD006882" \
     --tables /path/to/results
```

## Providing new Datasets
If you want to provide new datasets where you want to benchmark the models on, just exchange the "-gt" with you annotated mgf file which contains a "seq" key which holds the "ground-truth" peptide sequence. Moreover you need the prediction files / outputs from the other models and can provide them via the other command-line arguments as shown in 3.
