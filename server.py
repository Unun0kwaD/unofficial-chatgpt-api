"""Make some requests to OpenAI's chatbot"""

import time
import os
import flask
import sys
from flask import request, jsonify, g
import random
from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright

name = "app"
PROFILE_DIR = "/tmp/playwright" if '--profile' not in sys.argv else sys.argv[sys.argv.index('--profile') + 1]
PORT = 5001 if '--port' not in sys.argv else int(sys.argv[sys.argv.index('--port') + 1])
APP = flask.Flask(name)
PLAY = sync_playwright().start()
BROWSER = PLAY.firefox.launch_persistent_context(
user_data_dir=PROFILE_DIR,
headless=False,
java_script_enabled=True,
)
PAGE = BROWSER.new_page()

def get_input_box():
    """Get the child textarea of `PromptTextarea__TextareaWrapper`"""
    return PAGE.query_selector("textarea")

def is_logged_in():
    # See if we have a textarea with data-id="root"
    return get_input_box() is not None

def is_loading_response() -> bool:
    """See if the send button is diabled, if it does, we're not loading"""
    return PAGE.query_selector('button div.text-2xl') is not None



def is_finished_loading() -> bool:
    return PAGE.query_selector('div.overflow-hidden button:disabled') is not None

def send_message(message):
    # Send the message
    box = get_input_box()
    box.click()
    box.fill(message)
    box.press("Enter")

@APP.route("/lastmsg", methods=["GET"])
def get_last_message():
    """Get the latest message"""
    print("GETTING LAST MESSAGE")
    # while is_loading_response():
    #     time.sleep(0.25)
    # time.sleep(0.5)
    # while is_finished_loading():
    #     time.sleep(0.25)

      # Wait for the loading spinner to disappear
    PAGE.wait_for_selector('.loading-spinner', state='hidden')
    print("answer loading")
    
    # Wait for the send button to be enabled
    PAGE.wait_for_selector('button[aria-label="Stop generating"]', state='hidden')
    
    print("not loading")
    while True:
        page_elements = PAGE.query_selector_all(".markdown.prose")
        if page_elements != []:
            break
    last_element = page_elements.pop()
    return last_element.inner_text()

def regenerate_response():
    """Clicks on the Try again button.
    Returns None if there is no button"""
    try_again_button = PAGE.query_selector("button:has-text('Try again')")
    if try_again_button is not None:
        try_again_button.click()
    return try_again_button

#Okay, let’s go
@APP.route("/start", methods=["GET"])
def press_ok():

    ok_button=PAGE.query_selector(".btn.relative.btn-primary")
    print(ok_button.inner_text)
    if ok_button is not None:
        ok_button.click()
        ok_button.press("Enter")
    return ok_button

def get_reset_button():
    """Returns the reset thread button (it is an a tag not a button)"""
    return PAGE.query_selector("a:has-text('Reset thread')")

@APP.route("/chat", methods=["POST"]) 
def chat():
    try:
        data = request.get_json()
        message = data["q"]  # Assuming the key is "q" in the JSON data
        print(message)
    except KeyError:
        return jsonify({"error": "Invalid JSON format"}), 400

    print("Sending message: ", message)
    send_message(message)
    response = get_last_message()
    print("Response: ", response)
    return jsonify({"response": response})

# create a route for regenerating the response
@APP.route("/regenerate", methods=["POST"])
def regenerate():
    print("Regenerating response")
    if regenerate_response() is None:
        return "No response to regenerate"
    response = get_last_message()
    print("Response: ", response)
    return response

@APP.route("/reset", methods=["POST"])
def reset():
    print("Resetting chat")
    get_reset_button().click()
    return "Chat thread reset"

@APP.route("/restart", methods=["POST"])
def restart():
    global PAGE,BROWSER,PLAY
    PAGE.close()
    BROWSER.close()
    PLAY.stop()
    time.sleep(0.25)
    PLAY = sync_playwright().start()
    BROWSER = PLAY.chromium.launch_persistent_context(
        user_data_dir="/tmp/playwright",
        headless=False,
    )
    PAGE = BROWSER.new_page()
    PAGE.goto("https://chat.openai.com/")
    return "API restart!"


def start_browser():
    PAGE.goto("https://chat.openai.com/")
    if not is_logged_in():
        print("Please log in to OpenAI Chat")
        print("Press enter when you're done")
        input()
    else:
        print("Logged in")
        APP.run(port=6001, threaded=False)

if __name__ == "__main__":
    start_browser()


# curl -X POST -H "Content-Type: application/json" -d '{"q": "What is Banana"}' http://localhost:5001/chat
# curl -X GET http://localhost:5001/lastmsg