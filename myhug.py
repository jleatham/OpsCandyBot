import hug
import os
import requests
import json
import re
from datetime import datetime
from operator import itemgetter
from botFunctions import CANDY_EMAIL, CANDY_NAME




URL = "https://api.ciscospark.com/v1/messages"
PERSON_URL = "https://api.ciscospark.com/v1/people"
CARD_MSG_URL = "https://api.ciscospark.com/v1/attachment/actions"


CANDY_HEADERS = {
    'Authorization': os.environ['CANDY_TOKEN'],
    'Content-Type': "application/json",
    'cache-control': "no-cache"
}



@hug.post('/candy', examples='candy')
def candy(body):
    """
        Production for OpsCandy bot
        Takes the webhook data <body> and parses out the sender and the message
        Must filter out all messages sent by bot as those come back as part of webhook
        Strips the command of the botname, and then sends the command to take action
        Finally, we log the interaction in smartsheets

        Future: regex search identity for domain verification
    """
    email = CANDY_EMAIL
    headers = CANDY_HEADERS
    name = CANDY_NAME    
    print(f"GOT {type(body)}: {repr(body)}")
    resource = body["resource"]
    bot_event = body["event"]
    print(f'Resource = {resource}    Event = {bot_event}')
    if resource == "attachmentActions":
        card_id = body["data"]["messageId"]
        app_id = body["appId"]
        actor_id = body["actorId"]
        data_id = body["data"]["id"]
        person_id = body["data"]["personId"]
        room_id = body["data"]["roomId"]
        identity = get_person_from_id(person_id,headers)
        card_inputs = get_card_msg(data_id,headers)
        process_card_inputs(room_id,card_inputs,card_id, headers, name)
        print(f"{card_inputs}")
        #send_log_to_ss(name,str(datetime.now()),identity,f"card processed: {card_inputs['state_code']}",room_id)
        #create_card(room_id,headers)

    elif resource == "messages":
        room_id = body["data"]["roomId"]
        identity = body["data"]["personEmail"]
        text = body["data"]["id"]
        print("OpsCandy sees POST from {}".format(identity))
        if identity != email:
            print("{}-----{}".format(identity,email))
            #command = get_msg_sent_to_bot(text).lower()
            #command = get_msg_sent_to_bot(text, headers)
            #command = (command.replace(name, '')).strip()
            #command = (command.replace('@', '')).strip()
            #command = command.lower()  #added this, don't forget to move to events-bot as well
            #print("stripped command: {}".format(command))
            #process_bot_input_command(room_id,command, headers, name)
            #send_log_to_ss(name,str(datetime.now()),identity,command,room_id)
            create_card(room_id,headers)
    elif resource == "memberships":
        room_id = body["data"]["roomId"]
        identity = body["data"]["personEmail"]
        print(f'made it to memberships identity={identity}')
        if bot_event == "created" and identity == email:
            print("made it to if")
            create_card(room_id,headers)
            #send_log_to_ss(name,str(datetime.now()),identity,"new room: card created",room_id)
    print("Done processing webhook")



def process_bot_input_command(room_id,command, headers, bot_name):
    """ 
        Provides a few different command options based in different lists. (commands should be lower case)
        Combines all lists together and checks if any keyword commands are detected...basically a manually created case/switch statement
        For each possible command, do something
        Is there an easier way to do this?
    """

    
    #create a function to display who uses the bot the most (grab logs, count usage and return)
    command_list = [
        ("events",['event','events','-e']),
        ("mobile",['mobile','phone','-m']),
        ("filter",['filter','-f']),
        ("url_test",['url','-u']),
        ("test",['test','-t']),
        ("stats",['stats','-s'])
        #("command alias",["list of possible command entries"])
    ]
    result = command_parse(command_list,command)
    ##looks like: {"event":"TX FL AL","filter":"sec dc","mobile":""}
    if result:
        if "events" in result:
            print(f"made it to events:  {result['events']}") 
            state_filter = process_state_codes(result['events'].upper().split(" "),reverse=False)
    else:
        return

def remove_old_msgs(room_id,msg_ids_list,headers):
    payload = ""
    for id in msg_ids_list:
        url = f"https://api.ciscospark.com/v1/messages/{id}"
        response = requests.request("DELETE", url, data=payload, headers=headers)
        print(response.text)

def get_msg_sent_to_bot(msg_id, headers):
    urltext = URL + "/" + msg_id
    print(urltext)
    print(headers)
    payload = ""

    response = requests.request("GET", urltext, data=payload, headers=headers)
    response = json.loads(response.text)
    #print ("Message to bot : {}".format(response["text"]))
    print(str(response))
    return response["text"]

def get_person_from_id(person_id, headers):
    urltext = PERSON_URL + "/" + person_id
    payload = ""

    response = requests.request("GET", urltext, data=payload, headers=headers)
    response = json.loads(response.text)
    #print ("Message to bot : {}".format(response["emails"]))
    return response["emails"][0]


def get_card_msg(data_id, headers):
    urltext = CARD_MSG_URL + "/" + data_id
    payload = ""

    response = requests.request("GET", urltext, data=payload, headers=headers)
    response = json.loads(response.text)
    print ("Message to bot : {}".format(response))
    return response["inputs"]

def create_card(room_id,headers):
              
    markdown = "test"
    version = "1.0"

    explore_options = [ #turn into global
        ("meraki",["Meraki Sandbox"]),
        ("DNAC",["DNAC Sandbox"]),
        ("viptela",["Viptela Sandbox"]),
        ("ACI",["ACI Sandbox"]),
        ("internal",["Internal Server"])

    ]    
    filter_list = []
    for server in explore_options:  
        server_value = server[1][0]
        filter_list.append(f'{{"title": "{server_value}","value": "{server[0]}" }},')

    filter_options = "".join(filter_list)
    filter_options = filter_options[:-1] #remove last comma    

    body = (
        f'{{"type": "ColumnSet","columns": [{{"type": "Column","width": 2,"items": ['
        f'{{"type": "TextBlock","text": "OpsCandy Bot","weight": "Bolder","size": "Medium"}},'
        f'{{"type": "TextBlock","text": "Select which environment to explore:","wrap": true}},'
        f'{{"type": "TextBlock","text": "Filter Events by Architecture:","wrap": true}},'        
        f'{{"type": "Input.ChoiceSet","choices": [{filter_options}],"id":"filter_flag","title": "Server Options","isMultiSelect": false,"value": "meraki"}},'
        f'{{"type": "Input.Text","id": "old_msg_ids","isVisible": false,"value": ""}},'
        f'{{"type": "Input.Text","id": "button_choice","isVisible": false,"value": "new"}}'
        #f',{{"type": "Input.Toggle","title": "Mobile?","value": "false","wrap": false,"id" : "mobile_flag"}}'
        f']}}]}}'
        #mobile support for cards on Roadmap
    )
    card_payload = (
        f'{{'
        f'"roomId": "{room_id}",'
        f'"markdown": "{markdown}",'
        f'"attachments": [{{'
        f'"contentType": "application/vnd.microsoft.card.adaptive",'
        f'"content": {{"$schema": "http://adaptivecards.io/schemas/adaptive-card.json","type": "AdaptiveCard",'
        f'"version": "{version}","body": [{body}],'
        f'"actions": [{{"type":"Action.Submit","title":"Submit"}}]'
        f'}} }} ] }}'

    )     
    #payload = {"roomId": room_id,"markdown": message}
    #response = requests.request("POST", URL, data=json.dumps(payload), headers=headers)
    print(card_payload)
    response = requests.request("POST", URL, data=card_payload, headers=headers)
    #response = requests.post(URL, data=card_payload, headers=headers)
    
    #response = requests.request("POST", URL, data=json.dumps(card_payload), headers=headers)
    responseJson = json.loads(response.text)
    print(str(responseJson))
    return responseJson


def process_card_inputs(room_id,result,card_id,headers,bot_name ):
    msg_ids_list = []
    msg_ids_list.append(card_id)

    msg_ids_list = msg_ids_list + result["old_msg_ids"].split(",")
  
    remove_old_msgs(room_id,msg_ids_list,headers)

    if "create" in result["button_choice"]:
        create_card(room_id,headers)
    elif "new" in result["button_choice"]:
        if "meraki" in result["filter_flag"]:
            meraki_0_card(room_id,result,"meraki",headers)
        elif "DNAC" in result["filter_flag"]:
            pass     
        elif "viptela" in result["filter_flag"]:
            pass    
        elif "ACI" in result["filter_flag"]:
            pass   
        elif "internal" in result["filter_flag"]:
            pass                                
    else:
        #do something
        return


def meraki_0_card(room_id,result,api_source,headers):
    markdown = "API Seleciton Card"
    version = "1.0"
    
    #post table to teams
    api_flag_options = (
        f'{{"title": "Get Networks","value": "networks"}},'
        f'{{"title": "Get Clients","value": "clients"}}'
    )

    body = (
        f'{{"type": "Input.Text","id": "button_choice","isVisible": false,"value": "{api_source}"}},'
        f'{{"type": "Input.Text","id": "next_step","isVisible": false,"value": "1"}},'
        f'{{"type": "Input.ChoiceSet","choices": [{api_flag_options}],"id":"api_flag","title": "Select API","isMultiSelect": false,"value": ""}}'
        #mobile support for cards on Roadmap
    )

    card_payload = (
        f'{{'
        f'"roomId": "{room_id}",'
        f'"markdown": "{markdown}",'
        f'"attachments": [{{'
        f'"contentType": "application/vnd.microsoft.card.adaptive",'
        f'"content": {{"$schema": "http://adaptivecards.io/schemas/adaptive-card.json","type": "AdaptiveCard",'
        f'"version": "{version}","body": [{body}],'
        f'"actions": [{{"type":"Action.Submit","title":"Submit"}}]'
        f'}} }} ] }}'
    )


         
    #payload = {"roomId": room_id,"markdown": message}
    #response = requests.request("POST", URL, data=json.dumps(payload), headers=headers)
    print(card_payload)
    response = requests.request("POST", URL, data=card_payload, headers=headers)
    responseJson = json.loads(response.text)
    print(str(responseJson))


def bot_post_to_room(room_id, message, headers):
    print(f"msg byte size(UTF-8): {len(message.encode('utf-8'))} bytes")
    #try to post
    payload = {"roomId": room_id,"markdown": message}
    response = requests.request("POST", URL, data=json.dumps(payload), headers=headers)
    #error handling
    if response.status_code != 200:
        #modify function to receive user_input as well so we can pass through
        user_input = "some test message for the moment"
        #send to the DEVs bot room
        error_handling(response,response.status_code,user_input,room_id,headers)
    responseJson = json.loads(response.text)
    print(str(responseJson))
    return responseJson


def error_handling(response,err_code,user_input,room_id,headers):
    """
        if response is not 200 from webex.  COme here and check error msg
        Based on error, send user a help msg in their room and send the dev's room
        the actual error msg.
        
    """
    error = json.loads(response.text) #converts to type DICT
    #grabs the error response from teams
    #Example: {"message":"Unable to post message to room: \"The request payload is too big\"",
    #"errors":[{"description":"Unable to post message to room: \"The request payload is too big\""}],
    # "trackingId":"ROUTER_5C5510D1-D8A4-01BB-0055-48A302E70055"}

    #send to DEVs bot room
    message = ("**Error code**: {}  \n**User input**: {}  \n**Error**: {}".format(err_code,user_input,error["message"]))
    bot_post_to_room(os.environ['TEST_ROOM_ID'],message,headers)
    
    #need to add error handling here
    #if XYZ in response.text then, etc
    search_obj = re.search(r'7439|big',error["message"])
    if search_obj:
        message = "Too many results for Teams output, sending email instead:"
    else:
        message = "Looks like we've hit a snag! Sending feedback to the development team."
    bot_post_to_room(room_id,message,headers)


def format_code_print_for_bot(data,state,columns,msg_flag):
    """
        Take pre-sorted data [{},{},{},..] and apply markdown
        Webex does not allow for large data table formatting so code blocks(```) are used as alternative.
        Output is one single long markdown string

        Should find a way to pass in column data as a list as opposed to hard coding
    """
    #python string formatting is useful: {:*<n.x} --> * = filler char, (<,>,or ^) = align left,right, or center, n.x = fill for n spaces, cut off after x

    #    print ("\n DATA \n")
    #    print (data)
    #    print ("\n COLUMNS \n")
    #    print (columns)
    msg_list = []
    if msg_flag == "start":
        msg_list.append("**Events for {}**  \n".format(state))
    elif msg_flag == "data":
        msg_list.append(" \n```")
        column_str, spacer_str = row_format_for_code_print(columns,header=True)
        msg_list.append(column_str)
        msg_list.append(spacer_str)       
        for row_dict in data:
            msg_list.append(row_format_for_code_print(columns,row_dict=row_dict))
        msg_list.append("  \n```")
    elif msg_flag == "end":
        msg_list.append("  \n ")
        msg_list.append("Commands structure: \{events\} . . . \{filter\} . . . \{mobile\}  \n")
        msg_list.append("Example:  :: events CA NV WA filter sec dc mobile  \n")   
        msg_list.append("Example:  :: -e TX -f collab  -m  \n") 
        msg_list.append("Example:  :: events TX mobile   \n") 
    msg = ''.join(msg_list)
    return msg


