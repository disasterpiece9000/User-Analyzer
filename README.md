# /u/bot4bot is a user-analyzer script written by /u/shimmyjimmy97

## Call the bot via a comment with this with this syntax:
    /u/bot4bot someuser

## Call the bot via a PM with this syntax:
    /u/bot4bot someuser
or

    someuser

This bot is designed to give insight into a Reddit users history without having to snoop through pages and pages of comments. It does so by replying with a formatted list of these attributes:

* Date the account was created on
* Total post/comment karma
* Niceness score
* Negative karma subreddits
* Average sentence
* Most used subreddits
* Top 10 most used words

____

## Niceness Score:
This score is derived from a sentiment analysis of the user's comment text. This is done using [NLTK's](https://www.nltk.org/) built in sentiment analysis. The math behind how I get the niceness score is a bit hard to put into words, so I'll just post the relevant portion of code below:

```
total_sent = count_neg + count_pos
	if comment_count > 20 and total_sent > 10:
		sent_perc = (total_sent / float(comment_count)) * 100

		if sent_perc >= 7.5:
			pos_perc = (count_pos / float(total_sent)) * 100
			neg_perc = (count_neg / float(total_sent)) * 100
			diff_perc = pos_perc - neg_perc
```

If diff_perc is <= -20 then the user is considered negative, and if its >= 35 then the user is considered positive. **Clearly this formula is anything but scientific, so please take it with a grain of salt.** I arrived at these numbers by making minor adjustments until it seemed to be (more or less) accurate. This score can be thrown off by users who participate in communities that frequently use words that would be considered "negative" in another context. For instance, a user who visits /r/CFB might be identified as negative because they use words like "tackle".

