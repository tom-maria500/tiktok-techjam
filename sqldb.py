import streamlit as st
import mysql.connector
import pandas as pd

# Database connection parameters
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'tiktokmvcrm1223!',
    'database': 'tiktok_crm'
}

# Function to create database connection
def create_connection():
    return mysql.connector.connect(**db_config)

# Function to execute query and return results as DataFrame
def execute_query(query, params=None):
    conn = create_connection()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            result = cursor.fetchall()
        return pd.DataFrame(result)
    finally:
        conn.close()

def getClientInformation(clientName):
    query = 'SELECT * FROM client WHERE company_name = %s'
    clientInfo = execute_query(query, params=(clientName,))
    client_dict = clientInfo.to_dict('records')[0]

    #store all client information in variables
    # print(client_dict)
    return client_dict

# Streamlit app
st.write("demo")



#function to get all of the managers' direct reports' sales metrics
query = '''
    select u.fname, u.lname, um.total_sales, um.deals_closed, um.customer_satisfaction, um.conversion_rate, um.average_deal_size
    from user u
    left join usermetrics um
    on u.user_id = um.user_id 
    where u.managerID = 100000001
    order by um.total_sales desc
    '''
def getDirectReportsMetrics(userEmail):
    def getUserLoginId(userEmail):
        query = '''
        select user_id
        from user u 
        where email = %s
        '''
        result = execute_query(query, params=(userEmail,))
        managerId = result.iloc[0, 0] 
        return managerId
    
    managerID = getUserLoginId(userEmail)
    query = '''
    select u.fname, u.lname, um.total_sales, um.deals_closed, um.customer_satisfaction, um.conversion_rate, um.average_deal_size
    from user u
    left join usermetrics um
    on u.user_id = um.user_id 
    where u.managerID = %s
    order by um.total_sales desc
    '''
    metrics = execute_query(query, params=(managerID,))
    
    result = {}
    for row in metrics.itertuples(index=False):
        full_name = f"{row.fname} {row.lname}"
        result[full_name] = {
            "total_sales": row.total_sales,
            "deals_closed": row.deals_closed,
            "customer_satisfaction": row.customer_satisfaction,
            "conversion_rate": row.conversion_rate,
            "average_deal_size": row.average_deal_size
        }

    return result

def is_manager(userEmail):
    query = '''
        select managerID
        from user u 
        where email = %s
        '''
    result = execute_query(query, params=(userEmail,))
    managerId = result.iloc[0, 0] 
    print(managerId)
    print(managerId == None)
    return managerId == None

def getProfileInfo(userEmail):
    query = '''
    select * 
    from user where email = %s'''
    userInfo = execute_query(query, params=(userEmail,))
    client_dict = userInfo.to_dict('records')[0]

    #store all client information in variables
    print(client_dict)
    return client_dict

def getUserMetrics(userEmail):
    query = '''
    select * 
    from usermetrics um
    left join user u
    on um.user_id = u.user_id  where u.email = %s'''
    userInfo = execute_query(query, params=(userEmail,))
    client_dict = userInfo.to_dict('records')[0]

    #store all client information in variables
    print(client_dict)
    return client_dict

def getClientNames():
    query = '''
    select company_name 
    from client'''

    clientNames = execute_query(query)
    clientNames = clientNames['company_name'].tolist()
    return clientNames






    

# getClientInformation("Amazon")
#getDirectReportsMetrics(100000001)
#getUserLoginId("guru.vibha1@gmail.com")
#getProfileInfo("guru.vibha1@gmail.com")
getClientNames()