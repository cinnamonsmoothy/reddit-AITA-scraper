# imports:
import praw
import csv
from time import sleep
from datetime import datetime, timezone, timedelta
import math
import streamlit as st
from connection.mongo import MongoDBConnection




# streamlit app settings:
st.set_page_config(
    page_title='Reddit AITA Scraper',
    page_icon='favicon.png',
    initial_sidebar_state='collapsed',
)



# Custom CSS
st.markdown(open('style.css').read(), unsafe_allow_html=True)



# Reddit API credentials
reddit = praw.Reddit(client_id='obIaevVI8E2FoyDdQoPRMQ',
                     client_secret='AIshZPMpTUhhGV9DKgRTkbHbU6vvUA',
                     user_agent='post scraper hourly')

mongodb_connection = st.experimental_connection("mongodb", type=MongoDBConnection)

add_data = st.button(label="add data")
if add_data:
    mongodb_connection.insert({"a": 55, "b": 6})


tab1, tab2 = st.tabs(['Find Best Story', 'Query All Stories'])

# Function to scrape posts and write to CSV
def scrape_posts_to_csv(subreddit_name, hours_ago, min_comments):
    csv_file = 'posts.csv'
    current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    time_threshold = current_time - timedelta(hours=hours_ago)

    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['title', 'self_text', 'url', 'num_comments', 'time_ago', 'score'])

        for post in reddit.subreddit(subreddit_name).new(limit=None):
            if post.created_utc < time_threshold.timestamp():
                break
            if post.num_comments < min_comments:
                continue

            title = post.title
            self_text = post.selftext
            url = post.url
            created_utc = post.created_utc
            num_comments = post.num_comments
            time_ago = round(((current_time - datetime.utcfromtimestamp(created_utc).replace(tzinfo=timezone.utc)).total_seconds() / 60 / 60), 1)
            score = round(num_comments/time_ago, 1)

            writer.writerow([title, self_text, url, num_comments, time_ago, score])

# Function to query posts from posts.csv based on score threshold
def query_posts_by_score(score_threshold):
    posts = []
    with open('posts.csv', 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            score = float(row['score'])
            if score >= score_threshold:
                posts.append(row)
    return posts

with tab1:
# Streamlit App
    st.title("Reddit AITA Scraper")
    st.caption('This app finds the best story from AITA within the last few hours. Useful for finding stories to post onto Tiktok!')

    # User input using sliders
    with st.form("reddit_scraper_form"):
        hours_ago = st.slider("Hours ago posted", 1, 24, 5, step=1,
                              help="The more recent a post is on reddit, the more likely it is to go viral, because no one else has posted it!")
        min_comments = st.slider("Minimum number of comments", 0, 200, 60, step=5,
                                 help="The more comments a post has, the more interested people are, so this will tell you if its a good story!")

        submitted = st.form_submit_button("Run", use_container_width=True)

    with st.spinner('Grabbing Best Story...'):
        if submitted:
            # Scrape Reddit posts and write to CSV
            scrape_posts_to_csv('AmITheAsshole', hours_ago, min_comments)

            # Read the CSV and find the story with the highest score
            with open('posts.csv', 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                max_score = -1
                best_story = None
                for row in reader:
                    score = float(row['score'])
                    if score > max_score:
                        max_score = score
                        best_story = row

            if best_story:
                # Typing animation for the story title
                message_placeholder = st.empty()
                words = best_story['title'].split()
                for i in range(len(words)):
                    typed_text = " ".join(words[:i+1]) + "▌"
                    message_placeholder.subheader(typed_text)
                    sleep(0.001)  # Adjust the sleep duration to control the typing speed
                message_placeholder.subheader(best_story['title'])

                # Typing animation for the body text
                message_placeholder2 = st.empty()
                words = best_story['self_text'].split()
                for i in range(len(words)):
                    typed_text = " ".join(words[:i+1]) + "▌"
                    message_placeholder2.caption(typed_text)
                    sleep(0.001)  # Adjust the sleep duration to control the typing speed
                message_placeholder2.caption(best_story['self_text'])

                st.write("Comments:", best_story['num_comments'])
                st.write("Hours ago posted:", best_story['time_ago'])
                st.write("Score:", best_story['score'])
                st.write("URL:", best_story['url'])
            else:
                st.error('No posts found with that criteria :( Try increasing the hours/decreasing the min comments')
                
with tab2:
    
# Create a new tab for querying posts based on score
    st.title("Query Posts by Score")
    st.caption("This section queries all the stories collected from your last run in the 'Find Best Story' tab.")
    score_threshold = st.slider("Score Threshold", 1, 1000, 500, step=1,
                                help="Query all posts with a score greater than or equal to the chosen threshold.")
    query_button = st.button("Query Posts")

    if query_button:
        # Query posts based on score threshold
        queried_posts = query_posts_by_score(score_threshold)

        # Display the queried posts
        if queried_posts:
            for post in queried_posts:
                st.write(post['title'])
                st.write("Comments:", post['num_comments'])
                st.write("Hours ago posted:", post['time_ago'])
                st.write("Score:", post['score'])
                st.write("URL:", post['url'])
                st.divider()
        else:
            st.error("No posts found with the specified score threshold.")
