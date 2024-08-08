import streamlit as st
from streamlit_pills import pills
import pandas as pd
from tikapi import TikAPI, ValidationException, ResponseException
from openai import OpenAI
import dotenv
import os 

# Load environment variables and initialize APIs
api = TikAPI('ddiH5Fi2og1aKgslPrGXk4NBui8kStPsTlPHEVMkpoXetsnt')

dotenv.load_dotenv()
client_recommend_api = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def classify_industry(description):
    response = client_recommend_api.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": 
                """
                As an AI with expertise in language analysis and business, your task is to analyze the description of the TikTok video and determine what industry the ad is for. For example, if they promote clothing, it is the Fashion industry. State the industry the product is for. This should be a concise descriptor. If there is not enough information to determine the industry, return "null".
                Can you choose from the following industries: Fashion/Apparel, Beauty/Personal Care, Health/Wellness, Food/Beverages, Technology, Travel/Hospitality, Entertainment, Automotive, 
                Home/Living, Education, Financial Services, E-commerce, Luxury Goods, Toys/Games, Pets, or Real Estate. 
                """
            },
            {
                "role": "user",
                "content": description
            }
        ]
    )
    return response.choices[0].message.content

def classify_brand(description):
    response = client_recommend_api.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": 
                """
                As an AI with expertise in language analysis and business, your task is to analyze the description of the TikTok video and determine what company/brand the ad is for. It is typically following the '@' symbol, but this is not always the case. State just the company or brand name. 
                If there is not enough information to determine the company/brand, return "null".
                """
            },
            {
                "role": "user",
                "content": description
            }
        ]
    )
    return response.choices[0].message.content

def fetch_tiktok_data():
    try:
        # Get the hashtag ID for #adpartner
        response = api.public.hashtag(name="adpartner")
        hashtagId = response.json()['challengeInfo']['challenge']['id']

        # Fetch videos with the hashtag ID
        response = api.public.hashtag(id=hashtagId, count=30, country="us")

        data = []
        for item in response.json().get('itemList', []):
            video_id = item.get('id')
            author = item.get('author', {}).get('uniqueId')
            description = item.get('desc', '')
            views = item.get('stats', {}).get('playCount', 0)
            industry = classify_industry(description)
            brand = classify_brand(description)
            if brand != "null" and industry != "null":
                data.append({
                    "Author": author,
                    "Ad Views": views,
                    "Industry": industry,
                    "Brand": brand,
                    "Description": description
                })
        return pd.DataFrame(data)
    except (ValidationException, ResponseException) as e:
        st.error(f"An error occurred: {str(e)}")
        return pd.DataFrame()



