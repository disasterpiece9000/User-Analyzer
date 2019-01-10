# Imports
import praw
from praw.models import Comment
import prawcore
import sys
import time
import json
import math
from collections import Counter
from unidecode import unidecode
import datetime
import dateutil.parser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
from tinydb import TinyDB, Query
from fractions import gcd
import markovify
import re

# Sentiment analyzer
sid = SentimentIntensityAnalyzer()

# Start instance of Reddit
reddit = praw.Reddit('ShillDetector9000')

# Read stop words from files
with open('stopwords.txt', 'r') as words:
	stop_words = [word.lower().strip() for word in words]
allowed_chars = set(["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V"])
	
class POSifiedText(markovify.Text):
    def word_split(self, sentence):
        words = re.split(self.word_split_pattern, sentence)
        words = [ "::".join(tag) for tag in nltk.pos_tag(words) ]
        return words

    def word_join(self, words):
        sentence = " ".join(word.split("::")[0] for word in words)
        return sentence
        
    def test_sentence_input(self, sentence):
	    """
	    A basic sentence filter. This one rejects sentences that contain
	    the type of punctuation that would look strange on its own
	    in a randomly-generated sentence.
	    """
	    emote_pat = re.compile(r"\[.+?\]\(\/.+?\)")
	    reject_pat = re.compile(r"(^')|('$)|\s'|'\s|([\"(\(\)\[\])])|(~\ [\w\d\-_]{3,20}\ -----)")
	    # Decode unicode, mainly to normalize fancy quotation marks
	    decoded = unidecode(sentence)
	    # Sentence shouldn't contain problematic characters
	    filtered_str = re.sub(emote_pat, '', decoded).replace('  ',' ')
	    # Filtered sentence will have neither emotes nor double spaces
	    if re.search(reject_pat, filtered_str):
		    # Not counting emotes, there are no awkward characters.
		    return False
	    return True
        
# Turn username into user object and check if user exists
def setUser(username):
	user = reddit.redditor(username)
	try:
		user.fullname
	except (prawcore.exceptions.NotFound, AttributeError, prawcore.exceptions.BadRequest):
		return None
	return user

# Formats 2 numbers into a percent capped at 4 digits
def formatPercent(partial, total):
	percent = (float(partial) / float(total)) * 100
	if percent < 0:
		return str(percent)[:5] + '%'
	return str(percent)[:4] + '%'

# Analyze frequency of word usage
def analyzeWords(word_activity):
	return_str = '\n###Top 10 most used words:\nWord | # of times used\n---------|:----------:'
	for key, value in word_activity.most_common(10):
		hold_str = '\n' + str(key) + ' | ' + str(value)
		return_str += hold_str
	return return_str

# Analyze stats from comment sentiment analysis for general +/- label
def analyzeSentiment(comment_count, count_neg, count_pos):
	total_sent = count_neg + count_pos
	if comment_count > 20 and total_sent > 10:
		sent_perc = (total_sent / float(comment_count)) * 100

		if sent_perc >= 7.5:
			pos_perc = (count_pos / float(total_sent)) * 100
			neg_perc = (count_neg / float(total_sent)) * 100
			diff_perc = pos_perc - neg_perc

			if diff_perc <= -20:
				return ('This user seems to have a bad attitide. They are **negative**, with a sentiment score of: ' + str(diff_perc)[:5] + '%')
			elif diff_perc >= 35:
				return ('This user seems like a pretty nice person. They are **positive**, with a score of: ' + str(diff_perc)[:4] + '%')
			else:
				return ('This user seems pretty level headed. They are **neutral**, with a score of: ' + str(diff_perc)[:4] + '%')
	else:
		return ("This user doesn't have enough comments to determine if they are positive or negative. How mysterious")

# Analyze sub activity for breakdown of posts/comments by subreddit
def analyzeSubActivity(sub_activity, total_submiss):
	return_str = '\n###Most used Subreddits:\nSubreddit | # of posts/comments | % \n---------|:----------:|:----------:'
	for key, value in sub_activity.most_common(5):
		return_str += ('\n' + key + ' | ' + str(value) + ' | ' + formatPercent(value, total_submiss))
	return return_str

# Analyze posting times to find gaps larger than 1 month
def analyzeAccntActivity(accnt_activity, accnt_created):
	# Current time for end point of date range
	now = datetime.datetime.now()
	# Variable to be incremented by 1 day until date account created gets to current day
	parse_time = datetime.datetime.strptime(accnt_created, '%m/%d/%y')
	# Time difference between the current time and the date being itterated through
	t_delta = now - parse_time
	max_gap = 0
	current_gap = 0
	first_post_found = False
	while(t_delta.days >= 1):
		if accnt_activity[parse_time.strftime('%x')] > 0:
			current_gap = 0
			t_delta = now - parse_time
			if first_post_found == False:
				first_post_found = True
			parse_time += datetime.timedelta(days=1)
			continue
		elif first_post_found == True:
			current_gap += 1
			if current_gap > max_gap:
				max_gap = current_gap
		parse_time += datetime.timedelta(days=1)
		t_delta = now - parse_time

	if max_gap >= 30:
		gap_month = math.floor(max_gap/30)
		gap_days = max_gap % 30
		return ('**Warning: this section is probably inaccurate. Working on a fix now.** The user has a gap in their posting history for a period of ' + str(gap_month) + ' months and ' + str(gap_days) + ' days. Hmm I wonder what they were up to...')
	else:
		return None
		
def analyzeNegativeKarma(neg_count, all_count):
	neg_str = "They don't get along well with people from these subreddits: \n\nSubreddit | # negative comments |  \n---------|:----------:"
	for key, value in neg_count.most_common(5):
		if value >= 5 and (neg_count[key]/float(all_count[key])) >= 0.10:
			neg_str += ('\n' + key + ' | ' + str(value))
	if neg_str == "They don't get along well with people from these subreddits: \n\nSubreddit | # negative comments |  \n---------|:----------:":
		return None
	return neg_str
	

# Analyze the sentiment of the most frequently refferenced named entities
def analyzeSubjSent(subj_sent, subj_count):
	pos_sent = {}
	neg_sent = {}
	for key, value in subj_count.most_common(10):
		print('Subject: ' + key + ' Count: ' + str(subj_count[key]) + ' TotalSent: ' + str(subj_sent[key]))
		if value == 0:
			print('Skipping subject')
			continue
		if subj_sent[key] >= 2:
			pos_sent[key] = subj_sent[key]
		elif subj_sent[key] <= -2:
			neg_sent[key] = subj_sent[key]

	pos_str = ''
	neg_str = ''
	if len(pos_sent) > 0:
		pos_str += 'This user sure does seem to like: '
		for entity in pos_sent:
			pos_str += entity + ' '
	if len(neg_sent) > 0:
		neg_str += "Man oh man this user just can't stand: "
		for entity in neg_sent:
			neg_str += entity + ' '
	if pos_str == '' and neg_str == '':
		return None
	elif pos_str == '':
		return neg_str
	elif neg_str == '':
		return pos_str
	else:
		return pos_str + '\n\n' + neg_str

# Concatonates strings for comment/pm replyText
def concatReply(reply_list):
	reply_str = ''
	for section in reply_list:
		if section != None:
			reply_str += (section + '\n\n')
	reply_str += "-----\n\n[What is this?](https://www.reddit.com/user/bot4bot/comments/aecodj/welcome_to_ubot4bot/) | [Remove this comment](https://www.reddit.com/user/bot4bot/comments/aecx9n/remove_this_comment/) | [Contact the owner](https://www.reddit.com/user/shimmyjimmy97/)"
	return reply_str

# Analyze word frequency and sentiment for each sentence
def analyzeText(text, word_activity, subj_count, subj_sent, all_comments):
	subj_whitelist = ['who', 'that', 'this', 'what', 'people', 'anyone', 'user', 'users', 'someone', 'one', 'all']
	total_sentiment = 0
	sentences = markovify.split_into_sentences(text)
	for sentence in sentences:
		all_comments.append(sentence)
		sentiment = sid.polarity_scores(sentence)['compound']
		total_sentiment += sentiment
		
		tokenized_text = sentence.split(' ')
		for word in tokenized_text:
			word = word.lower()
			if word.isalpha()and word not in stop_words:
				word_activity[word] += 1
				
				
			#if token.dep_ == 'nsubj' and token.pos_ != 'PRON' and token.tag_ != 'PRP' and str(token.text.lower()) not in subj_whitelist:
				#subj_count[token.text.lower()] += 1
				#subj_sent[token.text.lower()] += sentiment
				#if sentiment > 0.5:
					#subj_sent[token.text.lower()] += 1
				#elif sentiment < -0.5:
					#subj_sent[token.text.lower()] += -1
				#print('Subject: ' + token.text.lower() + '\nSentence: ' + sentence + '\nScore: ' + str(sentiment))

	return total_sentiment

def markovChain(text):
	try:
		text_model = POSifiedText(text)
	except KeyError:
		return None
	avg_sentence = text_model.make_sentence(tries=10)
	if avg_sentence == None:
		return None
	return ('Average sentence: ' + avg_sentence)
	
def linkComment(message, reply_message):
	print ('Entered comment reply mode')
	oc_reply = "Sorry for the delay. /u/bot4bot is back up and running, with more features coming soon!\n\n[View your report here](https://www.reddit.com/user/bot4bot/comments/aectw1/bot_replies_megathread/)"
	megathread = reddit.submission(id='aectw1')
	author = message.author
	
	try:
		mt_comment = megathread.reply(reply_message)
		time.sleep(15)
	except praw.exceptions.APIException:
		print ('RateLimit: sleeping for 2 min')
		time.sleep(120)
		mt_comment = megathread.reply(reply_message)
		
	oc_reply += str(mt_comment.fullname)[3:]
	
	author.message('Sorry for the delay. Your report has been completed', oc_reply)
	
	oc_reply += "/)\n\n-----\n\n[What is this?](https://www.reddit.com/user/bot4bot/comments/aecodj/welcome_to_ubot4bot/) | [Remove this comment](https://www.reddit.com/user/bot4bot/comments/aecx9n/remove_this_comment/) | [Contact the owner](https://www.reddit.com/user/shimmyjimmy97/)"
	
	try:
		message.reply(oc_reply)
	except (praw.exceptions.APIException, prawcore.exceptions.Forbidden):
		print('Comment deleted')
		message.mark_read()
		
	message.mark_read()
	
	

# Controls the scraping of user's account info
def analyzeUser(user):
	# Counts posts/comments per sub
	sub_activity = Counter()
	# Counts words with stop words filtered out
	word_activity = Counter()
	# Counts day of posts/comments
	accnt_activity = Counter()
	# Counts number of times Named Entity is reffered to
	subj_count = Counter()
	# Counts entity sentiment
	subj_sent = Counter()
	# Counts karma
	karma_count = Counter()
	# Counts all comments
	all_com = Counter()
	# Counts negative comments
	neg_com = Counter()

	comment_count = 0
	post_count = 0
	count_neg = 0
	count_pos = 0
	all_comments = []

	comments = user.comments.new(limit = None)
	posts = user.submissions.new(limit = None)

	print('\tGetting comments')
	for comment in comments:
		# Log comment activity
		all_com[str(comment.subreddit)] += 1
		sub_activity[str(comment.subreddit)] += 1
		comment_score = comment.score
		karma_count[str(comment.subreddit)] += comment_score
		
		if comment_score < 0:
			neg_com[str(comment.subreddit)] += 1
		
		#comment_created = datetime.datetime.fromtimestamp(comment.created).strftime('%x')
		#accnt_activity[comment_created] += 1
		comment_count += 1

		comment_text = comment.body
		comment_sent = analyzeText(comment_text, word_activity, subj_count, subj_sent, all_comments)
		if comment_sent <= -0.5:
			count_neg += 1
		if comment_sent >= 0.6:
			count_pos += 1

	print('\tGetting posts')
	for post in posts:
		sub_activity[str(post.subreddit)] += 1
		karma_count[str(post.subreddit)] += post.score
		
		#post_created = datetime.datetime.fromtimestamp(post.created).strftime('%x')
		#accnt_activity[post_created] += 1
		post_count += 1
		
	#all_comments = '\n'.join(all_comments)
	all_comments = ' '.join(all_comments)
	total_submiss = comment_count + post_count
	accnt_created = datetime.datetime.fromtimestamp(user.created).strftime('%x')

	reply_list = []
	print('\tFormatting reply:')
	reply_list.append(str(user) + ' created on: ' + accnt_created)
	print('\t\tGot date created')
	reply_list.append('Link karma: ' + str(user.link_karma) + ' Comment karma: ' + str(user.comment_karma))
	print ('\t\tGot total karma')
	reply_list.append(analyzeSentiment(comment_count, count_neg, count_pos))
	print('\t\tGot sentiment')
	
	#activity_str = analyzeAccntActivity(accnt_activity, accnt_created)
	#print('\t\tGot account activity')
	#subj_str = analyzeSubjSent(subj_sent, subj_count)
	#print('Got subject sentiment')
	if comment_count > 10:
		try:
			markov_str = markovChain(all_comments)
		except IndexError:
			markov_str = None
		if(markov_str != None):
			reply_list.append(markov_str)
			print ('\t\tGot avg sentence')
	neg_table = analyzeNegativeKarma(neg_com, all_com)
	if(neg_table != None):
		reply_list.append(neg_table)
	print ('\t\tGot negative comment subs')
	reply_list.append(analyzeSubActivity(sub_activity, total_submiss))
	print('\t\tGot sub activity')
	reply_list.append(analyzeWords(word_activity))
	print('\t\tGot most used words')

	return concatReply(reply_list)

 # Main method
while(True):
	try:
		messages = reddit.inbox.unread()
		for message in messages:
			print ('Message: ' + message.body)
			message_text = message.body.split()
			
			if len(message_text) > 2:
				message.mark_read()
				print('Message not identified as an account call')
				continue
			elif len(message_text) == 2:
				accnt_call = message_text.pop(0)
				username = message_text.pop(0)
			elif len(message_text) == 1:
				username = message_text.pop(0)
				
				
			print ('Message about user: ' + username + ' accepted')
			if username.startswith("/u/"):
				target_user = username[3:]
			elif username.startswith("u/"):
				target_user = username[2:]
			else:
				target_user = username
			user = setUser(target_user)
			if user != None:
				print ('User set. Beginning analysis')
				reply_message = analyzeUser(user)
				if isinstance(message, Comment):
					linkComment(message, reply_message)
					print('Message resolved\n')
				else:
					try:
						message.reply(reply_message)
					except praw.exceptions.APIException:
						print('Comment deleted')
					message.mark_read()
					print('Message resolved\n')
			else:
				message.mark_read()
				print ('Message resolved')
		time.sleep(10)
	except:
		print ('ERROR: Server Error\nSleeping for 5 min')
		time.sleep(300)
		pass
