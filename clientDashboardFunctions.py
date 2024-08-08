import ast
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
import openai
import logging
import time
import os
import json
from tenacity import retry, stop_after_attempt, wait_random_exponential
# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPEN_API_KEY_CLIENT_DASHBOARD"))

assistant_id = "asst_HI5jDraznUXvlLmfmjqTmh8l"


def wait_for_run_completion(client, thread_id, run_id, sleep_interval=5):
        while True:
            try:
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
                if run.completed_at:
                    elapsed_time = run.completed_at-run.created_at
                    formatted_elapsed_time = time.strftime(
                        "%H:%M:%S", time.gmtime(elapsed_time)
                    )
                    print(f"Run completed in {formatted_elapsed_time}")
                    logging.info(f"Run completed in {formatted_elapsed_time}")
                    #get messages once run is complete
                    messages = client.beta.threads.messages.list(thread_id=thread_id)
                    last_message = messages.data[0]
                    response = last_message.content[0].text.value
                    print(f"{response}")
                    return response
                    
            except Exception as e:
                logging.error(f"an error occured while retrieving the run: {e}")
                break
            logging.info("Waiting for run to complete...")
            time.sleep(sleep_interval)


def generateTasks():
    thread_id = "thread_YauPdUhSEXzuXbMQggGgiSi0"

    #create a message
    message = "Can you list the three most important tasks to complete for the tiktok representative to complete after the meeting using the file titled Meeting Transcript with the most recent date? The entire response should be in a python list of length 3 where each item in list is a string with the task. Entire response should be less than 50 words. No other explanation or introduction should be part of response and output must be a python list with three strings in it that are the three tasks."
    message = client.beta.threads.messages.create (
        thread_id=thread_id,
        role="user",
        content=message
    )

    #run our assistant
    run = client.beta.threads.runs.create (
        thread_id=thread_id,
        assistant_id= assistant_id,
        instructions="please address the user with respect"
    )


    #RUN
    tasks = wait_for_run_completion(client=client, thread_id=thread_id, run_id=run.id)
    # Extract content between square brackets
    start_index = tasks.index('[')
    end_index = tasks.index(']') + 1
    list_string = tasks[start_index:end_index]

    # Convert string representation of list to actual Python list
    result_list = ast.literal_eval(list_string)
    print(result_list)
    print(type(result_list))
    returnedList = []
    for string in result_list:
        returnedList.append(string)
    return returnedList
    

def generateSentimentAnalysis():
        
        thread_id = "thread_PCXr587dqZnASq0MQr93xrD6"

        #create a message
        # message = "Can you read all files you have access to and generate a score out of 100 for sentiment analysis of how well client interaction is going. Your response must always be in a json format with the number as the key and the value as a short explanation behind of score that is about 2 sentences. JSON should only have 1 key-value pair with overall score with key and value enclosed in double quotes. they key is the number score and the value is 2 sentences. No other explanation or introduction should be part of response and response must always be in json format."
        message = """
        Can you read all files you have access to and generate a score out of 100 for sentiment analysis of how well client interaction is going. Your response must always be in a JSON format with the number as the key and the value as a short explanation behind the score that is about 2 sentences. JSON should only have 1 key-value pair with the overall score with key and value enclosed in double quotes. The key is the number score and the value is 2 sentences. No other explanation or introduction should be part of the response and the response must always be in JSON format.
        """
        message = client.beta.threads.messages.create (
            thread_id=thread_id,
            role="user",
            content=message
        )

        #run our assistant
        run = client.beta.threads.runs.create (
            thread_id=thread_id,
            assistant_id= assistant_id,
            instructions="please address the user with respect"
        )


        #RUN
        sentiment = wait_for_run_completion(client=client, thread_id=thread_id, run_id=run.id)
        print(sentiment)
        # Extract the JSON content
        json_content = sentiment[sentiment.index('{'):sentiment.rindex('}')+1]
        print(json_content)
        # Convert to Python dictionary
        result_dict = json.loads(json_content)

        print(type(result_dict))
        return result_dict



@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def summarize_email(email_body):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes emails."},
                {"role": "user", "content": f"Please summarize the following email in a concise manner:\n\n{email_body}"}
            ],
            max_tokens=150  # Adjust as needed
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Unable to summarize email."











#generateTasks("vs_G0ichcYATIwdL2x2TWYnBtm7")
#generateSentimentAnalysis("vs_G0ichcYATIwdL2x2TWYnBtm7")