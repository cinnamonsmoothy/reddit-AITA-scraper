# imports:
import praw
import csv
from time import sleep
from datetime import datetime, timezone, timedelta
import streamlit as st
from connection.mongo import MongoDBConnection
import logging
import toml


FORMAT = '%(asctime)s %(clientip)-15s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# streamlit app settings:
st.set_page_config(
    page_title='Reddit AITA Scraper',
    page_icon='favicon.png',
    initial_sidebar_state='collapsed',
)

# Custom CSS
st.markdown(open('style.css').read(), unsafe_allow_html=True)

# Reddit API credentials via reading the secrets.toml file
secrets = toml.load(".streamlit/secrets.toml")
client_id = secrets["reddit"]["client_id"]
client_secret = secrets["reddit"]["client_secret"]
user_agent = secrets["reddit"]["user_agent"]

reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    user_agent=user_agent
)

mongodb_connection = st.experimental_connection("mongodb", type=MongoDBConnection)


tab1, tab2 = st.tabs(['Find Best Story', 'Query All Stories'])


def save_to_mongo(connection, data):
    for key, value in data.items():
        connection.insert(value)
    logger.info(f"Data saved to mongodb instance {connection}")



def get_best_post():
    # Fetch data from MongoDB using the find method with the specified filter
    highest_score_post = None
    highest_score = 0

    # Retrieve all documents from the database
    all_documents = mongodb_connection.find({})

    # Iterate over all documents in the database
    for document in all_documents:
        # Check if the "score" field is present in the document
        if "score" in document:
            # Get the "score" value from the document
            score = document["score"]
            
            # Check if the current score is higher than the highest score
            if score > highest_score:
                highest_score = score
                highest_score_post = document

    # Display the document with the highest score
    if highest_score_post:
        return highest_score_post
    

def scrape_posts_to_dict(subreddit_name, hours_ago, min_comments):
    current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    time_threshold = current_time - timedelta(hours=hours_ago)

    posts_dict = {}

    for post in reddit.subreddit(subreddit_name).new(limit=None):
        if post.created_utc < time_threshold.timestamp():
            break
        if post.num_comments < min_comments:
            continue

        created_utc = post.created_utc
        time_ago = round(((current_time - datetime.utcfromtimestamp(created_utc).replace(tzinfo=timezone.utc)).total_seconds() / 60 / 60), 1)
        score = round(post.num_comments / time_ago, 1)

        post_info = {
            'title': post.title,
            'self_text': post.selftext,
            'url': post.url,
            'num_comments': post.num_comments,
            'time_ago': time_ago,
            'score': score,
        }

        posts_dict[post.id] = post_info

    return posts_dict



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
    posts = mongodb_connection.find({})
    keep_posts = []
    for post in posts:
        score = float(post['score'])
        if score >= score_threshold:
            keep_posts.append(post)
    return keep_posts

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
            # Delete all existing posts from mongo db
            mongodb_connection.delete({})

            # Scrape Reddit posts and save to mongodb
            data = scrape_posts_to_dict('AmITheAsshole', hours_ago, min_comments)
            save_to_mongo(mongodb_connection, data)

            # get the story with the highest score
            best_story = get_best_post()

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
