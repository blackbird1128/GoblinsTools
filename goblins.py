import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
import json
import argparse

def ask_for_confirmation(message , accepted_yes = ["yes", "y" ] , accepted_no = ["N","no" , "No"] , check_case = False ):
    """an helper function to ask for confirmation 
       return True if the message is confirmed, False otherwise"""
    answer = None
    answer_text = "(" + "/".join(accepted_yes) + "|" + "/".join(accepted_no) + ")"
    while answer == None:
        temp_answer = input(message + " " + answer_text + " : ")
        if temp_answer in accepted_yes:
            answer = True
        if temp_answer in accepted_no:
            answer = False
    return answer

def get_bad_words_tokens(badwords_file):
    """get all the banned tokens from a file """
    with open(badwords_file) as bw_data:
        bw_json_data = json.load(bw_data)
        return bw_json_data['bad_words_ids']

def merge_bad_words_tokens(*token_lists):
    """merge multiple list of tokens"""
    merged_tokens = []
    for tokens in token_lists:
        merged_tokens.extend(tokens)
    return merged_tokens

def encode_word_to_bad_tokens_list(word, tokenizer):
    """encode words to match tokens banned by NovelAI"""
    word = word.strip()
    badwords_list = [] 
    badwords_list.append(tokenizer(word)['input_ids'])
    badwords_list.append(tokenizer(" " + word)['input_ids'])
    badwords_list.append(tokenizer(word.capitalize())['input_ids'])
    badwords_list.append(tokenizer(" " + word.capitalize())['input_ids'])
    badwords_list.append(tokenizer(word.upper())['input_ids'])
    badwords_list.append(tokenizer(" " + word.upper())['input_ids'])
    return badwords_list

def create_badwords_file(tokens_list , filename):
    """create a file with tokens formated like the one used by NovelAI"""
    badwords_dict = {'bad_words_ids' : tokens_list}
    with open(filename , "w") as writing_file:
        writing_file.write(json.dumps(badwords_dict))

def split_word_list(wordlist , separator):
    """split a bloc of words (helper rename )"""
    return wordlist.split(separator)

def detect_openable_files(list_files):
    """return a tuple containing a list of openable files and the list of files that failed to be opened"""
    openable_files = []
    bad_files = []
    for bad_wordfile in list_files:
        try:
            file_openable = open(bad_wordfile , "r")
            file_openable.close()
            openable_files.append(bad_wordfile)
        except FileNotFoundError as e: # Note: this can still fail if you somehow manage to remove the files during the few ms before the processing
            print(f"{bad_wordfile} can't be opened, check the path or the permissions of the file ")
            bad_files.append(bad_wordfile)
    return openable_files , bad_files

def cli_merge_from_badwords_files( filenames , output_filename):
    """merge multiple badwords files"""
    badwords_tokens = []
    for bad_wordfile in filenames:
        badwords_tokens.extend(get_bad_words_tokens(bad_wordfile))
    create_badwords_file(badwords_tokens , output_filename)   

def cli_create_from_files(filenames,output_filename, separator):
    """create a badwords files using multiple files"""
    list_banned_words = []
    for listword_filename in filenames:
        with open(listword_filename, "r") as listword_file:
            file_content = ""
            for line in listword_file:
                file_content  += line
            splited_words = split_word_list(file_content , separator )
            list_banned_words.extend(splited_words)
    list_banned_words = list(set(list_banned_words)) # remove duplicates 
    banned_tokens = []
    for word in list_banned_words:
        banned_tokens.extend(encode_word_to_bad_tokens_list(word , tokenizer))
    create_badwords_file(banned_tokens , output_filename)

parser = argparse.ArgumentParser(description="various tools for badwords file used in NovelAI")
parser.add_argument("files" ,  action='append', nargs='+'  , help="the list of files used for the commands")
parser.add_argument("--merge" , action='store_true',   help="merge a arbitrary number of badwords files")
parser.add_argument("--create_from_file" , action='store_true' , help="create a badwords list from text files separated by a common separator")
parser.add_argument("--filename" , help="the output filename" ,default="output.badwords")
parser.add_argument("--separator" , default="\n",   help="define the separator used in the words files.")
args = parser.parse_args()

if not args.merge and not args.create_from_file:
    parser.print_help()

if args.merge and args.create_from_file:
    print("Please only use only one of the option at the same time.")

if args.merge:
    file_args = args.files[0]
    openable_files , bad_files = detect_openable_files(file_args)
    if len(openable_files ) <= 1:
        print("merging one or less file is not possible or useful ")
        exit()
    if len(bad_files) > 0:
        print("Some files failed to be opened, do you want to continue with the current files ? ")
        remaining_files = openable_files
        remaining_files_str = ",".join(remaining_files)
        print(f"remaining files: ({remaining_files_str})")
        if ask_for_confirmation("Do you want to process only the remaining files ?"):
            cli_merge_from_badwords_files(remaining_files , args.filename)
        else:
            exit()
    cli_merge_from_badwords_files(openable_files , args.filename)

if args.create_from_file:
    print("Note: If this is your first time running the programm this will take a while")
    print("Don't hesitate to stop the programm if the loading take to long as it will get faster each run")
    from transformers import GPT2TokenizerFast
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    file_args = args.files[0]
    openable_files , bad_files = detect_openable_files(file_args)
    if len(bad_files) > 0:
        print("Some files failed to be opened, do you want to continue with the current files ? ")
        remaining_files = openable_files
        remaining_files_str = ",".join(remaining_files)
        print(f"remaining files: ({remaining_files_str})")
        if ask_for_confirmation("Do you want to process only the remaining files ?"):
            cli_create_from_files(remaining_files, args.filename , args.separator)
        else:
            exit()
    cli_create_from_files(openable_files, args.filename , args.separator)
