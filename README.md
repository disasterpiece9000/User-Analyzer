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
This score is derived from a sentiment analysis of the user's comment text. This is done using [NLTK's](https://www.nltk.org/) built in sentiment analysis. If a comment is found to have a score that shows obvious sentiment (> 0.5 or < -0.5) then it is tallied as a positive/negative comment. To determine if a user is overall positive, negative, or neutral, the program finds the 

