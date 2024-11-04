import json
import streamlit as st
import supabase
from supabase import create_client, Client
from openai import OpenAI


#1 Setting openai client
OPENAI = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key = OPENAI)

#2 Setting supabase client
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

#3 Function to insert a new user into 'users' table
def insert_user(name: str, email: str):
  # insert data into the users table
  response = supabase.table("users").insert({"name": name, "email": email}).execute()
  # check for errors in the response and raise an exception if needed
  if response.data:
    print("User inserted successfully:", response.data)
  else:
    # raise an error if the insertion was not successful
    error_message = response.error.get("message") if response.error else st.write("Try using a different email.")
    raise RuntimeError(f"Failed to insert user: {error_message}")

#4 Function to get the value of the last inserted email  
def get_last_email():
    """
    Retrieve the most recent email from the 'users' table.

    Returns:
    - email (str or None): The most recent email if found, otherwise None.
    """
    response = supabase.table("users").select("email").order("id", desc=True).limit(1).execute()
    
    # check if the response contains data and extract the email
    if response.data and len(response.data) > 0:  # ensure there's at least one email
        return response.data[0]['email']  # return the email from the first row
    else:
        print("No email found in the response.")
        return None  # return None if no email is found

#5 Function to get the number of rows in the 'questions' table
def question_count():
    response = supabase.table("questions").select("*", count="exact").execute()

    # check for errors
    if response.data:
        return len(response.data)  # count of rows in the 'questions' table
    else:
        st.error(f"Error retrieving questions: {response.error}")
        return 0  # return 0 if there was an error

#6 Function to get the user ID from the 'users' table using the last email
def get_user_id_by_email():
    """
    Retrieve the user ID from the 'users' table using the last email.

    Returns:
    - user_id (int or None): The ID of the user if found, otherwise None.
    """
    # get the last email using the existing function
    last_email = get_last_email()  # now returns a string or None

    if last_email:
        # query the 'users' table to find the user with the specified email
        response = supabase.table('users').select('id').eq('email', last_email).execute()

        # check if the response contains data
        if response.data and len(response.data) > 0:
            return response.data[0]['id']  # get the 'id' from the first row of data
        else:
            print("No user found with the specified email.")
            return None  # return None if user not found
    else:
        print("Last email is None or invalid.")
        return None  # return None if no last email is available

#7 Function to send answers to database
def send_answers(user_selections, user_id):
    """
    Send user selections as a single row to the 'answers' table.

    Parameters:
    - user_selections (list): The list of user selections to be sent to the 'user_answer' column.
    - user_id (int): The ID of the user to be sent to the 'user_id' column.
    """
    # ensure that user_selections is not empty and user_id is provided
    if not user_selections or user_id is None:
        return
    # convert the user_selections list to a JSON string (or comma-separated string if preferred)
    user_answer_str = json.dumps(user_selections)
    # prepare the data for insertion
    data_to_insert = {
        "user_answer": user_answer_str,  # store the list as a JSON string in the database
        "user_id": user_id
    }
    # insert the data into the 'answers' table as a single row
    response = supabase.table("answers").insert(data_to_insert).execute()
    # Check if the response contains data
    if response.data:
        print("Answers inserted successfully:", response.data)
    else:
        # Handle the case where insertion failed (no data in response)
        error_message = response.get("message", "Unknown error occurred during insertion")
        print("Error inserting answers:", error_message)
        raise RuntimeError(f"Failed to insert answers: {error_message}")
    # Return response for further handling or logging (optional)
    return response

#8 Function to collect questions and answers from the database in string format
def get_formatted_questions_and_answers():
    """
    Fetches questions and corresponding answers from the database, formats them,
    and returns a string where each question is numbered, followed by its possible answers
    ranked from a) to h).

    Returns:
    - formatted_questions (str): Formatted string with numbered questions and answers.
    """

    # Initialize the list that will store the formatted string
    formatted_questions = []

    # Get the total number of questions
    total_questions = question_count()

    # Loop through each question
    for question_number in range(1, total_questions + 1):
        # Fetch the question text from the 'questions' table
        question_response = supabase.table('questions').select('question_text').eq('id', question_number).execute()
        
        if question_response.data:
            question_text = question_response.data[0]['question_text']
            # Append the question number and text to the formatted list
            formatted_questions.append(f"Question {question_number}: {question_text}")

            # Fetch the possible answers corresponding to the current question
            answer_response = supabase.table('possible_answers').select('Alternatives').eq('Question', question_number).execute()

            if answer_response.data:
                # Generate letter labels (a), b), c), etc.)
                letter_labels = 'abcdefgh'

                # Append each alternative answer with the corresponding letter
                for index, answer in enumerate(answer_response.data):
                    formatted_questions.append(f"   {letter_labels[index]}) {answer['Alternatives']}")

    # Join all formatted questions and answers into a single string with new lines separating them
    return "\n".join(formatted_questions)


#9 Function to send user answers to openai and return the personality analysis 
def analyze_answers(questions, answers):
    # philosophy professor's role 
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
              "content": (
                  f"""You are a philosophy professor analyzing a student's moral and personality. Focus on their decision-making process, moral reasoning and tendencies such as pacifism, collectivism, altruism, egoism, etc. Analyze their response to the following questions, along with the other alternatives, and provide constructive feedback. Highlight any inconsistencies or traits that emerge from their response. The structure should be as follows, with each bullet point between 1 and 3 lines:
                  - **How You Value Life:** your thoughts based on the answers
                  - **Utilitarianism:** your thoughts on how utilitarian they were and a brief explanation of what it means
                  - **Altruism vs Ego:** your thoughts on 'goody' vs egocentric
                  - **Nihilism and Pessimism:** if it is a constant theme on their answers, suggest visiting a psychiatrist
                  - **Skepticism vs Hope:** say whether the student likes to hope more or be more skeptical
                  - **Morality and Hypocrisy:** a brief analysis of the consistency of their choices and how it relates to the degree of certainty/solidity of their beliefs. if they seemed to value themselves too much, bring them down a peg
                  - **Knowledge:** briefly say whether they value knowledge enough
                  - **Freedom vs Collectivism:** self-explanatory                    
                  - **Universalism vs Relativism:** self-explanatory

                  **Conclusion:** Mention how their religious view, trust and definition of love relate to their answers. Mention how they view traditions and correlate it to knowledge and ignorance. And if they chose 'an emotion' for the love question (number 16), say at the end: 'Oh, and by the way, love is not an emotion, moron.' 
                  


Here are the questions and answers:

{questions}

Now, analyze the student's answer based on the given context, and provide insights into their moral outlook and personality. Write everything on the third-person."""
                )
            },
            {"role": "user", "content": f"{answers}"}],
        stream=False,
    )
    content = response.choices[0].message.content

    return content
    
#10 QA function to stop halucinations
def QA(analysis,questions,answers):

    # assistant's QA role
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
              "content": (f"""You are a Quality Analyst with strong logical and philosophical skills. Your task is to review the feedback of a test based on the questions and answers. Focus on whether the analysis makes sense and remains consistent with the context provided. Be neutral and objective in your corrections to ensure the quality of the feedback, and return the same format as the input feedback. For instance, if the feedback says that the user values individual freedom, check that against question 14 to see if it makes sense. If the user actually answered they value colectivism more, then correct the feedback by deleting the part that is wrong and rewriting it correctly. The same goes for other answers, check Altruism with question 3 (and maybe others), universalism with question 20, and etc.
                  
Here are the questions and answers:

Questions: {questions}

Answers: {answers}
"""
                )
            },
            {"role": "user", "content": f"{analysis}"}],
        stream=False,
    )

    content = response.choices[0].message.content

    return content

#11 Function to create a list of grades for each category
def radar_data(QA_response, categories):
    #simple data scientist role 
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
              "content": (
                  f"""You are a computer, and you have to create a list of integers between 1 and 5 that represent the grades for each category based on a specific feedback. The categories are the following: {categories}, and the format must be as such: [4,3,5,3,1,2], where each number represents the grade for each category, respectively.

                  For example, you see that the feedback claimed that the student is not pessimist at all, so for that category, you must return 1. If the next category is Hopefullness, analyze what the feedback says about skepticism and hope, and grade it accordingly.

                  **Remember:** You should only return the list, i.e. '[1,2,1,4,3,...]'. DON'T RETURN ANYTHING ELSE.
                  """
                )
            },
            {"role": "user", "content": f"The feedback is this: {QA_response}, create the list."}],
        stream=False,
    )
    content = response.choices[0].message.content

    # Split content based on ": "
    split_content = content.split(": ", 1)  # Only split at the first occurrence

    # Check if we successfully split into two parts
    if len(split_content) > 1:
        content = split_content[1].strip()  # Take the part after ": " and strip any extra spaces
    else:
        content = split_content[0].strip()  # If splitting fails, fallback to the original content

    # Output the result
    return content, st.write('lengthed content: ', content)

#12 Function to generate user scores for each question and category

def generate_user_scores(answer,categories):
    # Initialize empty dictionary to store user scores
    user_scores = []
    for category in categories:
        user_scores.append(0)

    # Iterate over each question and category
    #Question 1. You unsheath your sword…
    if answer[0]=='b)':
        user_scores[0] += 2
        user_scores[1] += 0
        user_scores[2] += 0.5
        user_scores[3] += -1
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += -1
        user_scores[7] += 0
        
    elif answer[0]=='c)':
        user_scores[0] += 1
        user_scores[1] += 1
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 1
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0
    else:
        user_scores[0] += -1
        user_scores[1] += 0.5
        user_scores[2] += -1
        user_scores[3] += 0.5   
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 1
        user_scores[7] += -1
    #Question 2. Your little sibling is suddenly recognized by the whole world as the new Savior, but he/she has to sacrifice himself/herself…
    if answer[1]=='a)':
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += 2
        user_scores[3] += 1
        user_scores[4] += 1
        user_scores[5] += -0.5
        user_scores[6] += -1
        user_scores[7] += 1
        
    elif answer[1]=='b)':
        user_scores[0] += 0
        user_scores[1] += 2
        user_scores[2] += 0
        user_scores[3] += 0.5
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += -2
        user_scores[7] += 0
    
    elif answer[1]=='c)':
        user_scores[0] += 0
        user_scores[1] += -2
        user_scores[2] += -1
        user_scores[3] += -0.5
        user_scores[4] += 1
        user_scores[5] += 0
        user_scores[6] += 2
        user_scores[7] += 1
    
    elif answer[1]=='d)':
        user_scores[0] += -2
        user_scores[1] += -2
        user_scores[2] += -1
        user_scores[3] += 2
        user_scores[4] += -1
        user_scores[5] += -1
        user_scores[6] += 2
        user_scores[7] += -1

    else: #e)
        user_scores[0] += 1
        user_scores[1] += -1
        user_scores[2] += 0
        user_scores[3] += 1   
        user_scores[4] += 1
        user_scores[5] += 0
        user_scores[6] += 1
        user_scores[7] += 0
    #Question 3. You go back in time to the most vulnerable moment of the world's greatest villain's infancy for a brief moment…
    if answer[2]=='a)':
        user_scores[0] += 1
        user_scores[1] += 1
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 1
        user_scores[6] += -1
        user_scores[7] += 0
        
    elif answer[2]=='b)':
        user_scores[0] += -1
        user_scores[1] += 2
        user_scores[2] += -1
        user_scores[3] += 1
        user_scores[4] += 1
        user_scores[5] += 0
        user_scores[6] += -1
        user_scores[7] += -1
    
    elif answer[2]=='c)':
        user_scores[0] += 2
        user_scores[1] += -1
        user_scores[2] += 1
        user_scores[3] += -2
        user_scores[4] += 1
        user_scores[5] += -1
        user_scores[6] += 0
        user_scores[7] += 1

    else: #d)
        user_scores[0] += 1
        user_scores[1] += -0.5
        user_scores[2] += 0.5
        user_scores[3] += -2   
        user_scores[4] += -0.5
        user_scores[5] += 0.5
        user_scores[6] += 0.5
        user_scores[7] += 0
    #Question 4. You become the owner of half of the world's money and military power, your priority, the first thing you do is...
    if answer[3]=='a)':
        user_scores[0] += 1
        user_scores[1] += 0.5
        user_scores[2] += 0.5
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += -1
        
    elif answer[3]=='b)':
        user_scores[0] += 1
        user_scores[1] += 0.5
        user_scores[2] += 0.5
        user_scores[3] += -0.5
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[3]=='c)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0.5
        user_scores[3] += -1
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += -1
        user_scores[7] += 0
    
    elif answer[3]=='d)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 1
        user_scores[3] += -1
        user_scores[4] += 1
        user_scores[5] += -0.5
        user_scores[6] += 1
        user_scores[7] += 1
    
    elif answer[3]=='e)':
        user_scores[0] += -1
        user_scores[1] += -2
        user_scores[2] += -1
        user_scores[3] += 2
        user_scores[4] += -1
        user_scores[5] += 0
        user_scores[6] += 1
        user_scores[7] += 0
    
    else: #f)
        user_scores[0] += -1
        user_scores[1] += -1
        user_scores[2] += -2
        user_scores[3] += 1   
        user_scores[4] += -1
        user_scores[5] += 0
        user_scores[6] += 2
        user_scores[7] += 0

    #Question 5. The love of your life, the one you hoped to spend an eternity with, is found to be a villain...
    if answer[4]=='a)':
        user_scores[0] += -1
        user_scores[1] += 1
        user_scores[2] += -1
        user_scores[3] += 1
        user_scores[4] += -1
        user_scores[5] += -0.5
        user_scores[6] += -0.5
        user_scores[7] += 1
        
    elif answer[4]=='b)':
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += 0.5
        user_scores[3] += -1
        user_scores[4] += 0.5
        user_scores[5] += 1
        user_scores[6] += 0.5
        user_scores[7] += -0.5
    
    elif answer[4]=='c)':
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += 0.5
        user_scores[3] += -1
        user_scores[4] += 2
        user_scores[5] += 0
        user_scores[6] += 1
        user_scores[7] += 0
    
    elif answer[4]=='d)':
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 1
        user_scores[5] += 0
        user_scores[6] += 0.5
        user_scores[7] += 1

    else: #e)
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += 0.5
        user_scores[3] += 0.5   
        user_scores[4] += -1
        user_scores[5] += 0
        user_scores[6] += -1
        user_scores[7] += 0
    
    #Question 6. You are a leader in a democratic country on the brink of civil war. You have the power to prevent it, but it would require using harsh and undemocratic methods.

    if answer[5]=='a)':
        user_scores[0] += 0
        user_scores[1] += 2
        user_scores[2] += 0.5
        user_scores[3] += 0.5
        user_scores[4] += -1
        user_scores[5] += 0.5
        user_scores[6] += -1
        user_scores[7] += 0
        
    elif answer[5]=='b)':
        user_scores[0] += -0.5
        user_scores[1] += 1
        user_scores[2] += -1
        user_scores[3] += 0
        user_scores[4] += 0.5
        user_scores[5] += 0.5
        user_scores[6] += 1
        user_scores[7] += -0.5
    
    elif answer[5]=='c)':
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += 0.5
        user_scores[3] += -1
        user_scores[4] += 1
        user_scores[5] += -1
        user_scores[6] += -1
        user_scores[7] += 1
    
    elif answer[5]=='d)':
        user_scores[0] += 0
        user_scores[1] += -0.5
        user_scores[2] += 1
        user_scores[3] += -1
        user_scores[4] += 0.5
        user_scores[5] += -1
        user_scores[6] += 0
        user_scores[7] += 0

    else: #e)
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += -0.5   
        user_scores[4] += -0.5
        user_scores[5] += 0.5
        user_scores[6] += -1
        user_scores[7] += 0

    #Question 7. You live with a spouse and two small children on a house you worked hard to afford. You notice someone breaking through your door at night...

    if answer[6]=='a)':
        user_scores[0] += -1
        user_scores[1] += 0.5
        user_scores[2] += -1
        user_scores[3] += 0.5
        user_scores[4] += 1
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += -1
        
    elif answer[6]=='b)':
        user_scores[0] += 1
        user_scores[1] += 0
        user_scores[2] += 0.5
        user_scores[3] += -0.5
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0.5
    
    elif answer[6]=='c)':
        user_scores[0] += 1
        user_scores[1] += -1
        user_scores[2] += 1
        user_scores[3] += -2
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += -0.5
        user_scores[7] += 0
    
    elif answer[6]=='d)':
        user_scores[0] += 1
        user_scores[1] += 0.5
        user_scores[2] += 0.5
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0

    else: #e)
        user_scores[0] += -1
        user_scores[1] += 0.5
        user_scores[2] += -1
        user_scores[3] += 0   
        user_scores[4] += 1
        user_scores[5] += 0
        user_scores[6] += 0.5
        user_scores[7] += 0

    #Question 8. You find out that a beloved public figure has committed a serious crime...
    
    if answer[7]=='a)':
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 1
        user_scores[5] += -0.5
        user_scores[6] += 0
        user_scores[7] += 0
        
    elif answer[7]=='b)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 1
        user_scores[3] += 0
        user_scores[4] += 0.5
        user_scores[5] += 0.5
        user_scores[6] += -0.5
        user_scores[7] += -0.5
    
    elif answer[7]=='c)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 0
        user_scores[3] += -1
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[7]=='d)':
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += 0
        user_scores[3] += 1
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0

    else: #e)
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += -1
        user_scores[3] += 1   
        user_scores[4] += -1
        user_scores[5] += 0
        user_scores[6] += 1
        user_scores[7] += -1

    #Question 9. You have the opportunity to gain immense knowledge and wisdom, but it will isolate you from human contact for a decade or more.
    
    if answer[8]=='a)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 1
        user_scores[3] += -0.5
        user_scores[4] += 0.5
        user_scores[5] += 1
        user_scores[6] += -1
        user_scores[7] += 0
        
    elif answer[8]=='b)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += -0.5
        user_scores[3] += 0
        user_scores[4] += -0.5
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[8]=='c)':
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += 0
        user_scores[3] += -0.5
        user_scores[4] += 0.5
        user_scores[5] += 1
        user_scores[6] += 1
        user_scores[7] += 0
    
    else: # d)
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += -0.5
        user_scores[3] += 0.5
        user_scores[4] += -1
        user_scores[5] += -1
        user_scores[6] += 1
        user_scores[7] += 0

    #Question 10. Think about your religion for a moment...
    
    if answer[9]=='a)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += -0.5
        user_scores[3] += 0
        user_scores[4] += 1
        user_scores[5] += 0
        user_scores[6] += 0.5
        user_scores[7] += 1
        
    elif answer[9]=='b)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += -1
        user_scores[3] += 1
        user_scores[4] += 1
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0.5
    
    elif answer[9]=='c)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0.5
        user_scores[3] += 0
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0.5
    
    elif answer[9]=='d)':
        user_scores[0] += 0
        user_scores[1] += -0.5
        user_scores[2] += 0.5
        user_scores[3] += -0.5
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += -0.5
        user_scores[7] += -1

    else: #e)
        user_scores[0] += 0
        user_scores[1] += -0.5
        user_scores[2] += 0.5
        user_scores[3] += -0.5   
        user_scores[4] += -0.5
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += -1

    #Question 11. How much is a life worth?
    
    if answer[10]=='a)':
        user_scores[0] += 1
        user_scores[1] += 0
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += -1
        user_scores[6] += 0
        user_scores[7] += 0
        
    elif answer[10]=='b)':
        user_scores[0] += 1
        user_scores[1] += 0
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += -1
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[10]=='c)':
        user_scores[0] += -1
        user_scores[1] += 1
        user_scores[2] += 0
        user_scores[3] += 0.5
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += -0.5
    
    elif answer[10]=='d)':
        user_scores[0] += 0.5
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0

    else: #e)
        user_scores[0] += -1
        user_scores[1] += -0.5
        user_scores[2] += 0
        user_scores[3] += 0   
        user_scores[4] += 0.5
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += -0.5

    #Question 12. What is your life worth?

    if answer[11]=='a)':
        user_scores[0] += -0.5
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 1
        user_scores[4] += -0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += -0.5
        
    elif answer[11]=='b)':
        user_scores[0] += 1
        user_scores[1] += -1
        user_scores[2] += -1
        user_scores[3] += 0
        user_scores[4] += 0.5
        user_scores[5] += -0.5
        user_scores[6] += 1
        user_scores[7] += -1
    
    elif answer[11]=='c)':
        user_scores[0] += 0.5
        user_scores[1] += 0.5
        user_scores[2] += -0.5
        user_scores[3] += -0.5
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0.5
        user_scores[7] += -1
    
    elif answer[11]=='d)':
        user_scores[0] += 0.5
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += -0.5
        user_scores[6] += 0
        user_scores[7] += -0.5

    else: #e)
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += -0.5
        user_scores[3] += -0.5   
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += 0.5
        user_scores[7] += -0.5

    #Question 13. Knowing that the average statistical value of a life worldwide is about 1 million dollars, how much is your life worth?
    
    if answer[12]=='a)':
        user_scores[0] += -1
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 1
        user_scores[4] += -0.5
        user_scores[5] += 0
        user_scores[6] += -0.5
        user_scores[7] += -0.5
        
    elif answer[12]=='b)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[12]=='c)':
        user_scores[0] += 1
        user_scores[1] += -0.5
        user_scores[2] += -1
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 1
        user_scores[7] += 0
    
    elif answer[12]=='d)':
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += -0.5
        user_scores[3] += 0
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += -0.5
        user_scores[7] += -0.5

    else: #e)
        user_scores[0] += 1
        user_scores[1] += -1
        user_scores[2] += -1
        user_scores[3] += -1   
        user_scores[4] += 1
        user_scores[5] += -1
        user_scores[6] += 0
        user_scores[7] += 0

    #Question 14. For you, what is more important: individual freedom or the greater good of the collective?
    
    if answer[13]=='a)':
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += 0.5
        user_scores[3] += 0
        user_scores[4] += 0.5
        user_scores[5] += 0.5
        user_scores[6] += -1
        user_scores[7] += 0
        
    elif answer[13]=='b)':
        user_scores[0] += -0.5
        user_scores[1] += -0.5
        user_scores[2] += 0
        user_scores[3] += -0.5
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += 1.5
        user_scores[7] += 0
    
    elif answer[13]=='c)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += -0.5
        user_scores[4] += 0.5
        user_scores[5] += -0.5
        user_scores[6] += 1
        user_scores[7] += 0
    
    elif answer[13]=='d)':
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += 1
        user_scores[3] += -1
        user_scores[4] += 1
        user_scores[5] += -1
        user_scores[6] += 0
        user_scores[7] += 0

    else: #e)
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += 0
        user_scores[3] += 0.5   
        user_scores[4] += -1.5
        user_scores[5] += 1
        user_scores[6] += -1.5
        user_scores[7] += 0

    #Question 15. How important is filial piety to you? How much thicker is blood compared to water?
    
    if answer[14]=='a)':
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += 1
        user_scores[3] += -0.5
        user_scores[4] += 1
        user_scores[5] += -1
        user_scores[6] += 0
        user_scores[7] += 0
        
    elif answer[14]=='b)':
        user_scores[0] += 0
        user_scores[1] += -0.5
        user_scores[2] += 0.5
        user_scores[3] += -0.5
        user_scores[4] += 0.5
        user_scores[5] += -0.5
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[14]=='c)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 0.5
        user_scores[3] += 0
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[14]=='d)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 0.5
        user_scores[3] += 0
        user_scores[4] += 0.5
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0

    elif answer[14]=='e)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 0.5
        user_scores[4] += -0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[14]=='f)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0.5
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0

    else: #g)
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += -1
        user_scores[3] += 1   
        user_scores[4] += -1
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0

    #Question 16. What is love to you?
    
    if answer[15]=='a)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 0.5
        user_scores[3] += -1
        user_scores[4] += 0.5
        user_scores[5] += -1.5
        user_scores[6] += 0
        user_scores[7] += 0
        
    elif answer[15]=='b)':
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += -0.5
        user_scores[5] += 1
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[15]=='c)':
        user_scores[0] += 0
        user_scores[1] += -0.5
        user_scores[2] += 0.5
        user_scores[3] += -1
        user_scores[4] += 1
        user_scores[5] += -0.5
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[15]=='d)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += -0.5
        user_scores[3] += 0.5
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0

    elif answer[15]=='e)':
        user_scores[0] += 0
        user_scores[1] += -0.5
        user_scores[2] += 0
        user_scores[3] += -0.5
        user_scores[4] += 0.5
        user_scores[5] += -0.5
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[15]=='f)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0

    else: #g)
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 0
        user_scores[3] += 0   
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0

    #Question 17. What is ignorance to you?
    
    if answer[16]=='a)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0
        
    elif answer[16]=='b)':
        user_scores[0] += 0
        user_scores[1] += -0.5
        user_scores[2] += -0.5
        user_scores[3] += 1
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[16]=='c)':
        user_scores[0] += 0
        user_scores[1] += 1
        user_scores[2] += 0
        user_scores[3] += 0.5
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[16]=='d)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += -0.5
        user_scores[3] += 0
        user_scores[4] += -0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0

    elif answer[16]=='e)':
        user_scores[0] += 0
        user_scores[1] += -0.5
        user_scores[2] += -1
        user_scores[3] += 1
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[16]=='f)':
        user_scores[0] += 0
        user_scores[1] += -1
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += -0.5
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0

    else: #g)
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 0
        user_scores[3] += 0   
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0

    #Question 18. Jarvis accidentally killed his friend Kloe when he hid her medicine as a prank. At what age, if any, would you consider him to be innocent?
    
    if answer[17]=='a)':
        user_scores[0] += 1
        user_scores[1] += -1
        user_scores[2] += -0.5
        user_scores[3] += 1
        user_scores[4] += 1
        user_scores[5] += -0.5
        user_scores[6] += 0
        user_scores[7] += 1.5
        
    elif answer[17]=='b)':
        user_scores[0] += 0.5
        user_scores[1] += -1
        user_scores[2] += -1
        user_scores[3] += -1
        user_scores[4] += 0
        user_scores[5] += -1
        user_scores[6] += 0
        user_scores[7] += 1
    
    elif answer[17]=='c)':
        user_scores[0] += 0.5
        user_scores[1] += 0
        user_scores[2] += -0.5
        user_scores[3] += 0.5
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 1
    
    elif answer[17]=='d)':
        user_scores[0] += 0.5
        user_scores[1] += 0.5
        user_scores[2] += 0
        user_scores[3] += 0.5
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0.5

    elif answer[17]=='e)':
        user_scores[0] += 0.5
        user_scores[1] += 0.5
        user_scores[2] += 0.5
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[17]=='f)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 1
        user_scores[3] += -0.5
        user_scores[4] += 0.5
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += -0.5

    else: #g)
        user_scores[0] += -0.5
        user_scores[1] += -1
        user_scores[2] += 1.5
        user_scores[3] += -1   
        user_scores[4] += 1
        user_scores[5] += -1
        user_scores[6] += 0.5
        user_scores[7] += -1

    #Question 19. How much do you trust others?
    
    if answer[18]=='a)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += -0.5
        user_scores[3] += 1
        user_scores[4] += -0.5
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0
        
    elif answer[18]=='b)':
        user_scores[0] += 0
        user_scores[1] += 0.5
        user_scores[2] += 0.5
        user_scores[3] += -1
        user_scores[4] += 0.5
        user_scores[5] += 0.5
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[18]=='c)':
        user_scores[0] += 0
        user_scores[1] += -0.5
        user_scores[2] += 1
        user_scores[3] += 0.5
        user_scores[4] += 1
        user_scores[5] += -1
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[18]=='d)':
        user_scores[0] += 0.5
        user_scores[1] += 1
        user_scores[2] += 0
        user_scores[3] += -0.5
        user_scores[4] += -1
        user_scores[5] += 1
        user_scores[6] += 0
        user_scores[7] += 0

    #Question 20. To what extent should culture influence morality? If you aren't sure, ask yourself whether you think killing is wrong regardless of someone's morals and culture (if yes, you are an universalist).
    
    if answer[19]=='a)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 2
        
    elif answer[19]=='b)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += 0
    
    elif answer[19]=='c)':
        user_scores[0] += 0
        user_scores[1] += 0
        user_scores[2] += 0
        user_scores[3] += 0
        user_scores[4] += 0
        user_scores[5] += 0
        user_scores[6] += 0
        user_scores[7] += -2
    

    return user_scores

def stardardize_scores(userScores):
    userScores = [min(score, 5) for score in userScores]
   
    # Normalize the scores to range from 1 to 5
    normalized_scores = [(score - min(userScores)) / (max(userScores) - min(userScores)) * 4.5 + 0.5 for score in userScores]
    
    return normalized_scores