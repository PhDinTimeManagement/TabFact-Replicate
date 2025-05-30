# encoding=utf8
import sys
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
import pandas
import json
import re
import string
from unidecode import unidecode
from multiprocessing import Pool
import multiprocessing
import time

with open('../data/freq_list.json') as f:
    vocab = json.load(f)

with open('../data/stop_words.json') as f:
    stop_words = json.load(f)

months_a = ['january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december']
months_b = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
a2b = {a: b for a, b in zip(months_a, months_b)}
b2a = {b: a for a, b in zip(months_a, months_b)}


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def augment(s):
    recover_dict = {}
    if 'first' in s:
        s.append("1st")
        recover_dict[s[-1]] = 'first'
    elif 'second' in s:
        s.append("2nd")
        recover_dict[s[-1]] = 'second'
    elif 'third' in s:
        s.append("3rd")
        recover_dict[s[-1]] = 'third'
    elif 'fourth' in s:
        s.append("4th")
        recover_dict[s[-1]] = 'fourth'
    elif 'fifth' in s:
        s.append("5th")
        recover_dict[s[-1]] = 'fifth'
    elif 'sixth' in s:
        s.append("6th")
        recover_dict[s[-1]] = 'sixth'

    for i in range(1, 10):
        if "0" + str(i) in s:
            s.append(str(i))
            recover_dict[s[-1]] = "0" + str(i)

    if 'crowd' in s or 'attendance' in s:
        s.append("people")
        recover_dict[s[-1]] = 'crowd'
        s.append("audience")
        recover_dict[s[-1]] = 'crowd'

    if any([_ in months_a + months_b for _ in s]):
        for i in range(1, 32):
            if str(i) in s:
                if i % 10 == 1:
                    s.append(str(i) + "st")
                elif i % 10 == 2:
                    s.append(str(i) + "nd")
                elif i % 10 == 3:
                    s.append(str(i) + "rd")
                else:
                    s.append(str(i) + "th")
                recover_dict[s[-1]] = str(i)

        for k in a2b:
            if k in s:
                s.append(a2b[k])
                recover_dict[s[-1]] = k

        for k in b2a:
            if k in s:
                s.append(b2a[k])
                recover_dict[s[-1]] = k

    return s, recover_dict

# This is pure string replacement
def replace_useless(s):
    s = s.replace(',', '')
    s = s.replace('.', '')
    s = s.replace('/', '')
    return s

# Sentence-to-table-cell Matching
'''
    @param inp: The tokenized input sentence (list of words)
    @param string: A span of text from the sentence we want to match
    @param indexes: Candidate cell positions (row, col) in tabs that might match the string
    @param tabs: The full table data (2D)
    @param threshold: How strict the matching criteria is? Higher means stricter.
'''
def get_closest(inp, string, indexes, tabs, threshold):
    # Early return if the string is a stop word
    if string in stop_words:
        return None

    dist = 10000
    # Clean the string by removing punctuation like commas, slashes, etc.
    rep_string = replace_useless(string)
    # Number of words in the cleaned string
    len_string = len(rep_string.split())

    # Find the minimum length difference
    minimum = []
    for index in indexes:
        entity = replace_useless(tabs[index[0]][index[1]])
        len_tab = len(entity.split())
        if abs(len_tab - len_string) < dist:
            minimum = [index]
            dist = abs(len_tab - len_string)
        elif abs(len_tab - len_string) == dist:
            minimum.append(index)

    # For each word in rep_string, look up how frequent it is in the reference vocabulary
    vocabs = []
    for s in rep_string.split(' '):
        vocabs.append(vocab.get(s, 10000)) # If not found, assume it's rare 10000

    # If a candidate has exactly the same length as the string, we can return it directly
    if dist == 0:
        return minimum[0]

    '''
    #--------------------Feature Construction--------------------
    '''

    # F0: Raw word count of the string
    feature = [len_string]

    # F1: Normalized negative distance. Larger means more similar (closer length)
    # Proportion
    feature.append(-dist / (len_string + dist + 0.) * 4)

    # F2: Reward rare words
    if any([(s.isdigit() and int(s) < 100) for s in rep_string.split()]):
        feature.extend([0, 0])

    # F3: Reward very rare words more
    else:
        # Quite rare words
        if max(vocabs) > 1000:
            feature.append(1)
        else:
            feature.append(-1)
        # Whether contain super rare words
        if max(vocabs) > 5000:
            feature.append(3)
        else:
            feature.append(0)

    # F4: Reward longer spans
    if len_string > 1:
        feature.append(1)
    else:
        feature.append(0)

    # F5: If only one candidate, trust it more
    if len(indexes) == 1:
        feature.append(1)
    else:
        feature.append(0)

    # F6: Check if string length is more than distance -> good match
    if len_string > dist:
        feature.append(1)
    else:
        feature.append(0)

    # F7: Bonus if candidate has alternative forms (like "John Smith"
    cand = replace_useless(tabs[minimum[0][0]][minimum[0][1]])
    if '(' in cand and ')' in cand:
        feature.append(2)
    else:
        feature.append(0)

    # F8: Match to table header row? Boost score
    if minimum[0][0] == 0:
        feature.append(2)
    else:
        feature.append(0)

    # F9: Bonus if string contains month names
    if any([" " + _ + " " in " " + rep_string + " " for _ in months_a + months_b]):
        feature.append(5)
    else:
        feature.append(0)

    # F10: Penalty if string doesn't appear in candidate cell
    if rep_string in cand:
        feature.append(0)
    else:
        feature.append(-5)

    if sum(feature) > threshold:
        # If there are multiple "best" (same minimum length difference) candidates
        # We need to resolve the ambiguity
        if len(minimum) > 1:
            # Check if the first match is not in the header row (row > 0)
            if minimum[0][0] > 0:
                # Return a special tag [-2, col] to indicate that the match was ambiguous but belongs to a data row
                return [-2, minimum[0][1]]
            # Otherwise, just return it normally as the chosen cell
            else:
                return minimum[0]
        # If there's only one best match, just return that directly
        else:
            return minimum[0]
    # If the overall feature score was too low, it means: "no good match"
    else:
        return None


def replace_number(string):
    string = re.sub(r'(\b)one(\b)', r'\g<1>1\g<2>', string)
    string = re.sub(r'(\b)two(\b)', '\g<1>2\g<2>', string)
    string = re.sub(r'(\b)three(\b)', '\g<1>3\g<2>', string)
    string = re.sub(r'(\b)four(\b)', '\g<1>4\g<2>', string)
    string = re.sub(r'(\b)five(\b)', '\g<1>5\g<2>', string)
    string = re.sub(r'(\b)six(\b)', '\g<1>6\g<2>', string)
    string = re.sub(r'(\b)seven(\b)', '\g<1>7\g<2>', string)
    string = re.sub(r'(\b)eight(\b)', '\g<1>8\g<2>', string)
    string = re.sub(r'(\b)nine(\b)', '\g<1>9\g<2>', string)
    string = re.sub(r'(\b)ten(\b)', '\g<1>10\g<2>', string)
    string = re.sub(r'(\b)eleven(\b)', '\g<1>11\g<2>', string)
    string = re.sub(r'(\b)twelve(\b)', '\g<1>12\g<2>', string)
    string = re.sub(r'(\b)thirteen(\b)', '\g<1>13\g<2>', string)
    string = re.sub(r'(\b)fourteen(\b)', '\g<1>14\g<2>', string)
    string = re.sub(r'(\b)fifteen(\b)', '\g<1>15\g<2>', string)
    string = re.sub(r'(\b)sixteen(\b)', '\g<1>16\g<2>', string)
    string = re.sub(r'(\b)seventeen(\b)', '\g<1>17\g<2>', string)
    string = re.sub(r'(\b)eighteen(\b)', '\g<1>18\g<2>', string)
    string = re.sub(r'(\b)nineteen(\b)', '\g<1>19\g<2>', string)
    string = re.sub(r'(\b)twenty(\b)', '\g<1>20\g<2>', string)
    return string


# transliterate is a Python dictionary that
# maps ASCII-normalized versions of words back to their original non-ASCII versions
# For example, "café" might be mapped to "cafe"
def replace(w, transliterate):
    if w in transliterate:
        return transliterate[w]
    else:
        return w

# No usage in the code and no idea what it does
def intersect(w_new, w_old):
    new_set = []
    for w_1 in w_new:
        for w_2 in w_old:
            if w_1[:2] == w_2[:2] and w_1[2] > w_2[2]:
                new_set.append(w_2)
    return new_set

# For e.g., playing => play
def recover(buf, recover_dict, content):
    if len(recover_dict) == 0:
        return buf
    else:
        new_buf = []
        for w in buf.split(' '):
            if w not in content:
                new_buf.append(recover_dict.get(w, w))
            else:
                new_buf.append(w)
        return ' '.join(new_buf)

'''
    @param inp: The original input string
    @param backbone: A map of lemmatized words to their (row, col) positions in the table
    @param trans_backbone: Same as above, but for transliterated tokens
    @param transliterate: Dict to recover the original word from its transliterated form
    @param tabs: The table content as a 2D list
    @param recover_dicts: One per cell: used to undo lemmatization or normalization
    @param repeat: Tracks repeated tokens for handling multi-word pharases
    @param threshold: Matching threshold for the get_closest function
    
    Say your sentence is: "John Moss received 69.9 percent"
    - You're building up "John Moss" → matches (1, 0).
    - Now you hit "received", which doesn’t match that table cell.
    
    So:
    - Finalize "John Moss" → #John Moss;1,0#
    - Append it to new_str
    - Tag it as 'ENT'
    - Start new buffer with "received".
'''
def postprocess(inp, backbone, trans_backbone, transliterate, tabs, recover_dicts, repeat, threshold=1.0):
    # Initialize variables
    new_str = []
    new_tags = []
    buf = ""
    pos_buf = []
    last = set()
    prev_closest = []

    # Lemmatize the sentence and get its POS tags
    inp, _, pos_tags = get_lemmatize(inp, True)

    # Loop over words and process them
    for w, p in zip(inp, pos_tags):

        # CASE 1: For word in backbone (original form from table)
        # Check if the word is part of a repeatable phrase or it's a new token in buffer
        if (w in backbone) and ((" " + w + " " in " " + buf + " " and w in repeat) or (" " + w + " " not in " " + buf + " ")):
            # If the buffer is empty, start buffering this word and track possible positions
            if buf == "":
                last = set(backbone[w])
                buf = w
                pos_buf.append(p)
            else:
                # If the buffer is not empty, intersect with prior matches
                proposed = set(backbone[w]) & last
                # Of no overlap, run get_closest to finalize the buf and map to a table cell
                if not proposed:
                    closest = get_closest(inp, buf, last, tabs, threshold)
                    if closest:
                        # Use recover to restore the fomatting
                        # Format as "#...;row,col#"
                        buf = '#{};{},{}#'.format(recover(buf,
                                                    recover_dicts[closest[0]][closest[1]],
                                                    tabs[closest[0]][closest[1]]),
                                                    closest[0], closest[1])

                    # Push to new_str, marks as 'ENT' in new_tags
                    new_str.append(buf)
                    if buf.startswith("#"):
                        new_tags.append('ENT')
                    # Otherwise, it's just regular words, so we add back their POS tags (stored in pos_buf)
                    else:
                        new_tags.extend(pos_buf)
                    pos_buf = []
                    buf = w
                    last = set(backbone[w])
                    pos_buf.append(p)
                else:
                    last = proposed
                    buf += " " + w
                    pos_buf.append(p)

        # CASE 2: Word is in transliterated backbone
        # Same logic as above, but now you're working with transliterate[w] and trans_backbone[w]
        elif w in trans_backbone and ((" " + w + " " in " " + buf + " " and w in repeat) or (" " + w + " " not in " " + buf + " ")):
            if buf == "":
                last = set(trans_backbone[w])
                buf = transliterate[w]
                pos_buf.append(p)
            else:
                proposed = set(trans_backbone[w]) & last
                if not proposed:
                    closest = get_closest(inp, buf, last, tabs, threshold)
                    if closest:
                        buf = '#{};{},{}#'.format(recover(buf, recover_dicts[closest[0]][closest[1]],
                                                          tabs[closest[0]][closest[1]]), closest[0], closest[1])
                    new_str.append(buf)
                    if buf.startswith("#"):
                        new_tags.append('ENT')
                    else:
                        new_tags.extend(pos_buf)
                    pos_buf = []
                    buf = transliterate[w]
                    last = set(trans_backbone[w])
                    pos_buf.append(p)
                else:
                    buf += " " + transliterate[w]
                    last = proposed
                    pos_buf.append(p)

        # CASE 3: Word doesn't match any table cell
        # This reset the buffer, inserts the unmatched word, and its POS tag
        else:
            if buf != "":
                closest = get_closest(inp, buf, last, tabs, threshold)
                if closest:
                    buf = '#{};{},{}#'.format(recover(buf, recover_dicts[closest[0]][closest[1]],
                                                      tabs[closest[0]][closest[1]]), closest[0], closest[1])
                new_str.append(buf)
                if buf.startswith("#"):
                    new_tags.append('ENT')
                else:
                    new_tags.extend(pos_buf)
                pos_buf = []

            buf = ""
            last = set()
            new_str.append(replace_number(w)) # Replace three with 3
            new_tags.append(p)

    # Till here, the for loop ends
    # Final check for leftover buffer
    if buf != "":
        closest = get_closest(inp, buf, last, tabs, threshold)
        if closest:
            buf = '#{};{},{}#'.format(recover(buf, recover_dicts[closest[0]][closest[1]],
                                              tabs[closest[0]][closest[1]]), closest[0], closest[1])
        new_str.append(buf)
        if buf.startswith("#"):
            new_tags.append('ENT')
        else:
            new_tags.extend(pos_buf)
        pos_buf = []

    # First string: sentence with matched table cells like #Moss;1,0# won election
    # Second string: corresponding tags for each word in the sentence like 'ENT', 'VB', 'NN'
    return " ".join(new_str), " ".join(new_tags)

# This function lemmatizes the words in a sentence
def get_lemmatize(words, return_pos):
    #words = nltk.word_tokenize(words)
    recover_dict = {}
    words = words.strip().split(' ')
    pos_tags = [_[1] for _ in nltk.pos_tag(words)]
    word_roots = []
    for w, p in zip(words, pos_tags):
        if is_ascii(w) and p in tag_dict:
            lemm = lemmatizer.lemmatize(w, tag_dict[p])
            if lemm != w:
                recover_dict[lemm] = w
            word_roots.append(lemm)
        else:
            word_roots.append(w)
    if return_pos:
        return word_roots, recover_dict, pos_tags
    else:
        return word_roots, recover_dict


tag_dict = {"JJ": wordnet.ADJ,
            "NN": wordnet.NOUN,
            "NNS": wordnet.NOUN,
            "NNP": wordnet.NOUN,
            "NNPS": wordnet.NOUN,
            "VB": wordnet.VERB,
            "VBD": wordnet.VERB,
            "VBG": wordnet.VERB,
            "VBN": wordnet.VERB,
            "VBP": wordnet.VERB,
            "VBZ": wordnet.VERB,
            "RB": wordnet.ADV,
            "RP": wordnet.ADV}

lemmatizer = WordNetLemmatizer()


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def merge_strings(name, string, tags=None):
    buff = ""
    inside = False
    words = []

    for c in string:
        if c == "#" and not inside:
            inside = True
            buff += c
        elif c == "#" and inside:
            inside = False
            buff += c
            words.append(buff)
            buff = ""
        elif c == " " and not inside:
            if buff:
                words.append(buff)
            buff = ""
        elif c == " " and inside:
            buff += c
        else:
            buff += c

    if buff:
        words.append(buff)

    tags = tags.split(' ')
    assert len(words) == len(tags), "{} and {}".format(words, tags)

    i = 0
    while i < len(words):
        if i < 2:
            i += 1
        elif words[i].startswith('#') and (not words[i - 1].startswith('#')) and words[i - 2].startswith('#'):
            if is_number(words[i].split(';')[0][1:]) and is_number(words[i - 2].split(';')[0][1:]):
                i += 1
            else:
                prev_idx = words[i - 2].split(';')[1][:-1].split(',')
                cur_idx = words[i].split(';')[1][:-1].split(',')
                if cur_idx == prev_idx or (prev_idx[0] == '-2' and prev_idx[1] == cur_idx[1]):
                    position = "{},{}".format(cur_idx[0], cur_idx[1])
                    candidate = words[i - 2].split(';')[0] + " " + words[i].split(';')[0][1:] + ";" + position + "#"
                    words[i] = candidate
                    del words[i - 1]
                    del tags[i - 1]
                    i -= 1
                    del words[i - 1]
                    del tags[i - 1]
                    i -= 1
                else:
                    i += 1
        else:
            i += 1

    return " ".join(words), " ".join(tags)


def sub_func(inputs):
    name, entry = inputs
    backbone = {}
    trans_backbone = {}
    transliterate = {}
    tabs = []
    recover_dicts = []
    repeat = set()
    with open('../data/all_csv/' + name, 'r') as f:
        for k, _ in enumerate(f.readlines()):
            #_ = _.decode('utf8')
            tabs.append([])
            recover_dicts.append([])
            for l, w in enumerate(_.strip().split('#')):
                #w = w.replace(',', '').replace('  ', ' ')
                tabs[-1].append(w)
                if len(w) > 0:
                    lemmatized_w, recover_dict = get_lemmatize(w, False)
                    lemmatized_w, new_dict = augment(lemmatized_w)
                    recover_dict.update(new_dict)
                    recover_dicts[-1].append(recover_dict)
                    for i, sub in enumerate(lemmatized_w):
                        if sub not in backbone:
                            backbone[sub] = [(k, l)]
                            if not is_ascii(sub):
                                trans_backbone[unidecode(sub)] = [(k, l)]
                                transliterate[unidecode(sub)] = sub
                        else:
                            if (k, l) not in backbone[sub]:
                                backbone[sub].append((k, l))
                            else:
                                if sub not in months_a + months_b:
                                    repeat.add(sub)
                            if not is_ascii(sub):
                                trans_backbone[unidecode(sub)].append((k, l))
                                transliterate[unidecode(sub)] = sub

                    for i, sub in enumerate(w.split(' ')):
                        if sub not in backbone:
                            backbone[sub] = [(k, l)]
                            if not is_ascii(sub):
                                trans_backbone[unidecode(sub)] = [(k, l)]
                                transliterate[unidecode(sub)] = sub
                        else:
                            if (k, l) not in backbone[sub]:
                                backbone[sub].append((k, l))
                            if not is_ascii(sub):
                                trans_backbone[unidecode(sub)].append((k, l))
                                transliterate[unidecode(sub)] = sub
                else:
                    recover_dicts[-1].append({})
                    #raise ValueError("Empty Cell")

    # Masking the caption
    captions, _ = get_lemmatize(entry[2].strip(), False)
    for i, w in enumerate(captions):
        if w not in backbone:
            backbone[w] = [(-1, -1)]
        else:
            backbone[w].append((-1, -1))
    tabs.append([" ".join(captions)])

    results = []
    for i in range(len(entry[0])):
        orig_sent = entry[0][i]
        if "=" not in orig_sent:
            sent, tags = postprocess(orig_sent, backbone, trans_backbone,
                                     transliterate, tabs, recover_dicts, repeat, threshold=1.0)
            if "#" not in sent:
                sent, tags = postprocess(orig_sent, backbone, trans_backbone,
                                         transliterate, tabs, recover_dicts, repeat, threshold=0.0)
            sent, tags = merge_strings(name, sent, tags)
            if not results:
                results = [[sent], [entry[1][i]], [tags], entry[2]]
            else:
                results[0].append(sent)
                results[1].append(entry[1][i])
                results[2].append(tags)
        else:
            # print("drop sentence: {}".format(orig_sent))
            continue

    return name, results


def get_func(filename, output):
    with open(filename) as f:
        data = json.load(f)
    r1_results = {}
    names = []
    entries = []

    for name in data:
        names.append(name)
        entries.append(data[name])

    cores = multiprocessing.cpu_count()
    pool = Pool(cores)

    r = pool.map(sub_func, zip(names, entries))
    print("there are {} tables".format(len(r)))
    #s_time = time.time()
    # for i in range(100):
    #    r = [sub_func((names[i], entries[i]))]
    #r = sub_func(('1-12221135-3.html.csv', data['1-12221135-3.html.csv']))
    #print("spent {}".format(time.time() - s_time))

    pool.close()
    pool.join()

    return dict(r)


results1 = get_func('../collected_data/r1_training_all.json', '../tokenized_data/r1_training_cleaned.json')
print("finished part 1")
results2 = get_func('../collected_data/r2_training_all.json', '../tokenized_data/r2_training_cleaned.json')
print("finished part 2")

# Pure addition of simple reasoning and complex reasoning
results2.update(results1)
with open('../tokenized_data/full_cleaned.json', 'w+') as f:
    # A function from Python’s built-in json module that serializes (converts) a Python object to JSON format and writes it directly to a file.
    json.dump(results2, f, indent=2)
