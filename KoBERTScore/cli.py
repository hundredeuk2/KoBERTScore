import argparse
import os
import warnings
from bokeh.io import save
from Korpora import Korpora
from transformers import BertModel, BertTokenizer

from .about import __name__, __version__
from .tasks import find_best_layer
from .utils import train_idf, idf_numpy_to_embed


def main():
    parser = argparse.ArgumentParser(description='Ko-BERTScore Command Line Interface')
    subparsers = parser.add_subparsers(help='Ko-BERTScore tasks')

    # Show package version
    parser_version = subparsers.add_parser('version', help='Show package version')
    parser_version.set_defaults(func=version)

    # Finding best layer
    parser_best_layer = subparsers.add_parser('best_layer', help='Finding best layer')
    parser_best_layer.add_argument('--model_name_or_path', type=str, required=True, help='BERT model path or name')
    # Will be implemented
#     parser_best_layer.add_argument('--references', type=str, help='References path')
#     parser_best_layer.add_argument('--candidates', type=str, help='Candidates path')
#     parser_best_layer.add_argument('--qualities', type=str, help='Qualities path')
#     parser_best_layer.add_argument('--idf_path', type=str, default=None, help='Pretrained IDF path')
    parser_best_layer.add_argument('--corpus', type=str, choices=['korsts'], help='STS corpus in Korpora')
    parser_best_layer.add_argument('--rescale_base', type=float, default=0.0, help='Rescale base value')
    parser_best_layer.add_argument('--batch_size', type=int, default=128, help='BERT embedding batch size')
    parser_best_layer.add_argument('--draw_plot', dest='draw_plot', action='store_true')
    parser_best_layer.add_argument('--plot_path', type=str, default=None, help='Directory for saving figures')
    parser_best_layer.set_defaults(func=best_layer)

    args = parser.parse_args()
    task_function = args.func
    task_function(args)


def version(args):
    print(f'{__name__}=={__version__}')


def best_layer(args):
    print(f'Finding best performance BERT layer with {args.model_name_or_path}')

    if not -1 < args.rescale_base < 1:
        raise ValueError("`rescale_base` must be in [-1, 1]")
    if args.draw_plot and args.plot_path is None:
        raise ValueError('Set `plot_path` when use `draw_plot`')

    # Load pretrained BERT model and tokenizer
    tokenizer = BertTokenizer.from_pretrained(args.model_name_or_path)
    encoder = BertModel.from_pretrained(args.model_name_or_path)

    # Load STS corpus
    corpus = Korpora.load('korsts')
    references = []
    candidates = []
    qualities = []
    for data in (corpus.train, corpus.dev):
        for example in data:
            references.append(example.text)
            candidates.append(example.pair)
            qualities.append(example.label)

    # Train IDF
    idf = train_idf(tokenizer, references)
    idf_embed = idf_numpy_to_embed(idf)

    # Find best layer
    model_name = args.model_name_or_path.split(os.path.sep)[-1]
    best_layer, informations = find_best_layer(
        tokenizer, encoder, references, candidates, qualities,
        idf=idf_embed, rescale_base=args.rescale_base,
        model_name=model_name, batch_size=args.batch_size
    )

    print(f'  - Best performance layer : {best_layer}')

    # Save figures
    if args.draw_plot:
        dirname = os.path.abspath(args.plot_path)
        print(f'Saving figures at {dirname}')
        os.makedirs(dirname, exist_ok=True)
        warnings.filterwarnings("ignore")
        save(informations['figures']['R'], f'{dirname}/R.html')
        save(informations['figures']['P'], f'{dirname}/P.html')
        save(informations['figures']['F'], f'{dirname}/F.html')


if __name__ == '__main__':
    main()