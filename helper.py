#%%
from __future__ import annotations #fixes type checking for a class within itself
from selenium import webdriver
#from selenium.webdriver import WebDriver
from time import sleep
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from typing import List
from bs4 import BeautifulSoup

import os
from getpass import getpass
if not os.path.isfile('secret.py'): #TODO: robustify
    with open('secret.py', 'w') as f:
        f.write('email = "' + input('discord email: ') + '"\n')
        f.write('pw = "' + getpass('discord password: ') + '"\n')
        f.write('mudae_channel = "' + input('mudae discord channel link: ') + '"\n')
import secret


class HelperBot: #should rename to DiscordMessanger or DiscordDriver - and maybe have it subclass the driver?
    """An object which helps interact with a 'standard' discord page"""
    #TODO: make more generally applicable to any discord use - maybe rename from HelperBot

    #CONSTANTS
    text_field_element_selector = '#app-mount > div.app-1q1i1E > div > div.layers-3iHuyZ.layers-3q14ss > div > div > div > div.content-98HsJk > div.chat-3bRxxu > div > main > form > div > div > div > div > div.textArea-12jD-V.textAreaSlate-1ZzRVj.slateContainer-3Qkn2x > div.markup-2BOw-j.slateTextArea-1Mkdgw.fontSize16Padding-3Wk7zP > div'

    def __init__(self):
        self.text_field: WebElement

        self.driver = webdriver.Chrome()
        self.login()
        WebDriverWait(self.driver, timeout=15, poll_frequency=1).until(lambda d: d.find_element_by_class_name('container-1r6BKw'))
        self.driver.get(secret.mudae_channel)
        WebDriverWait(self.driver, timeout=15, poll_frequency=1).until(lambda d: d.find_element_by_css_selector(HelperBot.text_field_element_selector))
        #self.text_field = self.driver.find_element_by_css_selector(HelperBot.text_field_element_selector)
        self.scroll_to_bottom()
        self.username: str
        self.username = ''.join(self.driver.find_element_by_class_name('nameTag-3uD-yy').text.split('\n'))

    @property
    def text_field(self):
        WebDriverWait(self.driver, timeout=10, poll_frequency=0.02).until(lambda d: d.find_element_by_css_selector(HelperBot.text_field_element_selector))
        return self.driver.find_element_by_css_selector(HelperBot.text_field_element_selector)

    def login(self):
        self.driver.get('https://discord.com/login')
        WebDriverWait(self.driver, timeout=15, poll_frequency=0.2).until(lambda d: d.find_element_by_xpath('//*[@id="app-mount"]/div[2]/div/div[2]/div/div/form/div/div/div[1]/div[3]/div[1]/div/input'))
        self.driver.find_element_by_xpath('//*[@id="app-mount"]/div[2]/div/div[2]/div/div/form/div/div/div[1]/div[3]/div[1]/div/input').send_keys(secret.email)
        self.driver.find_element_by_xpath('//*[@id="app-mount"]/div[2]/div/div[2]/div/div/form/div/div/div[1]/div[3]/div[2]/div/input').send_keys(secret.pw)
        self.driver.find_element_by_xpath('//*[@id="app-mount"]/div[2]/div/div[2]/div/div/form/div/div/div[1]/div[3]/button[2]').click()

    def send_message(self, text: str):
        """sends a message to the chat and returns the Message object in the chat"""
        most_recent_message = Message.get_context(self.driver)[0]
        self.text_field.send_keys(''.join([text, '\n']))
        my_message = text #replace text with Message object once found using the helper function
        def message_in_chat(driver):
            nonlocal most_recent_message
            nonlocal my_message
            static_context = Message.get_context(driver) #don't want it to append items to context in another thread
            for msg in static_context:
                if msg.context_index >= most_recent_message.context_index:
                    most_recent_message = static_context[0]
                    return False
                elif msg.author == self.username and msg.web_element.find_element_by_class_name('messageContent-2qWWxC').text == text:
                    my_message = msg
                    return True
                #if the message author is me, and the message contents are what i sent, then
        WebDriverWait(self.driver, timeout=10, poll_frequency=0.001).until(message_in_chat, 'tried finding sent message in chat')
        return my_message
    
    def scroll_to_bottom(self): #TODO: rewrite with js & self.driver.execute_script
        self.driver.find_element_by_class_name('public-DraftStyleDefault-block').send_keys('in:mudae-rolls'+Keys.ENTER)
        WebDriverWait(self.driver, timeout=10, poll_frequency=0.2).until(lambda d: d.find_elements_by_class_name('hit-1fVM9e'))
        self.driver.find_element_by_class_name('hit-1fVM9e').find_element_by_class_name('header-23xsNx').click()
        self.driver.find_element_by_class_name('jumpButton-JkYoYK').click()
        self.driver.find_element_by_class_name('icon-38sknP').click()

    def scroll_chat_down(self):
        Message.get_context(self.driver)
        #self.driver.find_element_by_class_name('scroller-2LSbBU').click()
        #TODO: fix focusing issure
        self.driver.execute_script('arguments[0].click()', self.driver.find_element_by_class_name('scroller-2LSbBU'))
        webdriver.ActionChains(self.driver).send_keys(Keys.END).perform()
        # myabe change Message.get_context to take driver as a param instead of bot (so that i could use 'd' in the lambda function - although i don't know if it matters)
        # page has loaded if ~the page is at the bottom of the chat~ or ~the page has loaded any new messages (since all new messages load at once)~
        WebDriverWait(self.driver, timeout=20, poll_frequency=0.02).until(lambda d: len(d.find_elements_by_class_name('wrapper-3vR61M')) < 2 or Message._context[0] != Message.get_context(d)[0])

class Message:
    """Wrapper for 'message' WebElements within the discord html"""
    _context: List[Message]
    _context = [] #holds messages based on what an associated HelperBot sees - in newest frist order
    running_get_context = False
    
    #CONSTANTS
    message_element_class_name = 'message-2qnXI6'
    message_element_group_start_class_name = 'groupStart-23k01U' # a sepecial message element that is at the beginning of multiple messages from the same person
    author_element_class_name = 'username-1A8OIy'
    bot_verif_element_class_name = 'botText-1526X_'
    reactions_element_class_name = 'reaction-1hd86g' 

    def __init__(self, element: WebElement, driver, context_index=None, group_starter=None): 
        self._web_element: WebElement
        self._web_element = element
        #print(self.web_element.text)
        #self.web_element.screenshot('message.png')
        self.id: str
        self.id = self._web_element.get_property('id')

        self.driver = driver
        
        self.context_index: int
        self.context_index = context_index


        self.content: str
        self.content = self.web_element.find_element_by_class_name('messageContent-2qWWxC').text

        self.is_group_starter: bool
        self.is_group_starter = Message.message_element_group_start_class_name in self.web_element.get_attribute('class').split(' ')

        self.group_starter: Message
        if self.is_group_starter:
            self.group_starter = self
        else:
            self.group_starter = group_starter

        self._author: str
        if self.is_group_starter:
            try:
                driver.execute_script('arguments[0].click()', self.web_element.find_element_by_class_name(Message.author_element_class_name))
                self._author = ''.join(driver.find_element_by_class_name('nameTag-m8r81H').text.split('\n'))
                driver.execute_script('arguments[0].click()', self.web_element.find_element_by_class_name(Message.author_element_class_name))
            except NoSuchElementException:
                #can occur because of pinned messages
                self._author = 'Pin'
            #except StaleElementReferenceException: # replace the wait at the beginning of the try with this if it doesn't work
            #    Message.running_get_context
            #    self._author = 'Unknown'
        else:
            self._author = None #None means unknown in this context

        self._is_from_bot: bool
        if self.is_group_starter:
            try:
                self.web_element.find_element_by_class_name(Message.bot_verif_element_class_name)
                self._is_from_bot = True
            except NoSuchElementException:
                self._is_from_bot = False
        else:
            self._is_from_bot = None
            
        self.is_viewed = False

    @property
    def web_element(self):
        return self.driver.find_element_by_id(self.id)

    @property
    def author(self) -> str:
        if self.group_starter is not None and self._author is None:
            self._author = self.group_starter._author
        return self._author
    
    @property
    def is_from_bot(self):
        if self.group_starter is not None and self._is_from_bot is None:
            self._is_from_bot = self.group_starter._is_from_bot
        return self._is_from_bot

    @staticmethod
    def get_context(driver) -> List[Message]:
        #I think that we never want two different threads to be running this at the same time 
        # - I may be doing this in a completely dumb way
        WebDriverWait(driver, timeout=30, poll_frequency=0.001).until_not(lambda d: Message.running_get_context)
        Message.running_get_context = True

        #get rid of stale messages
        fresh_old_messages: List[Message]
        fresh_old_messages = []
        for old_message in Message._context:
            old_message: Message
            try:
                #use any method for a staleness check
                old_message.web_element.is_enabled()
                fresh_old_messages.append(old_message)
            except StaleElementReferenceException:
                old_message.context_index = None # this should not be necessary for anything
        
        #repalce Message._context with the new messages (while not rewriting old messages that are still fresh)
        web_elements: List[WebElement]
        web_elements = driver.find_elements_by_class_name(Message.message_element_class_name)[::-1] #newest first order
        new_context: List[Message]
        new_context = []
        fresh_old_messages_start_index = None
        for i, web_element in enumerate(web_elements):
            if i >= 40: #only allow Message._context to hold max of 40 elements
                break
            #this only fully makes sense if we are never scrolling upward
            elif len(fresh_old_messages) > 0 and web_element.get_property('id') == fresh_old_messages[0].id:
                new_context.extend(fresh_old_messages)
                fresh_old_messages_start_index = i
                if len(new_context) > 40:
                    new_context = new_context[:40]
                break
            new_message = Message(web_element, driver)
            new_context.append(new_message) #appends by newest first
        i = len(new_context)-1
        while i >= 0:
            #update message old indices to match new messages
            if fresh_old_messages_start_index is not None and i >= fresh_old_messages_start_index:
                new_context[i].context_index = i
                i -= 1
                continue
            #guarantee that new_context[i] has a group_starter
            if new_context[i].group_starter is None:
                if i+1 < len(new_context):
                    new_context[i].group_starter = new_context[i+1].group_starter
                else: #pop the last element if no group_starter
                    new_context.pop()
                    i -= 1
                    continue
            #classify type of message
            if new_context[i].is_from_bot:
                new_context[i] = MudaeMessage(new_context[i].web_element, driver, context_index=i, group_starter=new_context[i].group_starter)
                if LotteryMessage.is_lottery_message(new_context[i]): #check if lottery message
                    new_context[i] = LotteryMessage(new_context[i].web_element, driver, context_index=i, group_starter=new_context[i].group_starter)
            else:
                new_context[i].context_index = i
            i -= 1
        #set context
        Message._context = new_context
        Message.running_get_context = False
        return Message._context

    def __repr__(self):
        str_rep = \
            f'''MESSAGE OBJECT:
                    \tid - {self.id}
                    \tauthor - {self.author},
                    \tis_group_starter - {self.is_group_starter},
                    \tgroup_starter.id - {self.group_starter.id},
                    \tcontext_index - {self.context_index},
                    \tsubclass - {type(self).__name__},
                    \tcontent - {self.content}
                    '''
        return str_rep

    def __eq__(self, other: Message) -> bool:
        return self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

class MudaeMessage(Message): #message from a bot (not necessarily Mudae) - TODO: make more robust to ensure message is from Mudae
    
    def __init__(self, element: WebElement, driver,  context_index=None, group_starter=None):
        Message.__init__(self, element, driver, context_index=context_index, group_starter=group_starter)

        assert self.is_from_bot, 'Message is not from a bot'

class LotteryMessage(MudaeMessage):
    #CONSTANTS
    character_name_element_class_name = 'embedAuthorName-3mnTWj'
    embed_description_element_class_name = 'embedDescription-1Cuq9a'
    message_footer_element_class_name = 'embedFooterText-28V_Wb'

    def __init__(self, element: WebElement, driver, context_index=None, group_starter=None):
        MudaeMessage.__init__(self, element, driver, context_index=context_index, group_starter=group_starter)
        
        #assert self.is_lottery_message(), f'This is not a LotteryMessage {self}'

        self.character: str
        self.character = self.web_element.find_element_by_class_name(LotteryMessage.character_name_element_class_name).text
        
        self.value: int
        self.value = int(self.web_element.find_element_by_class_name(LotteryMessage.embed_description_element_class_name).find_element_by_tag_name('strong').text)
        
        self.is_married: bool
        try:
            message_footer = self.web_element.find_element_by_class_name(LotteryMessage.message_footer_element_class_name).text
            self.is_married = 'Belongs to' in message_footer
        except NoSuchElementException:
            self.is_married = False

    def click_reaction(self, bot: HelperBot, index=0):
        reaction_elements: List[WebElement]
        WebDriverWait(bot.driver, timeout=10, poll_frequency=0.01).until(
            lambda d: self.web_element.find_elements_by_class_name(Message.reactions_element_class_name))
        reaction_elements = self.web_element.find_elements_by_class_name(Message.reactions_element_class_name)
        reaction_start_state = 'reactionMe-wv5HKu' in reaction_elements[index].get_attribute('class')
        print(self.web_element.text)
        bot.driver.execute_script('arguments[0].click()', reaction_elements[index].find_element_by_class_name('reactionInner-15NvIl'))
        print('click')
        reaction_end_state = 'reactionMe-wv5HKu' in reaction_elements[index].get_attribute('class')
        assert reaction_start_state != reaction_end_state, f'start_state: {reaction_start_state}, end_state: {reaction_end_state}'

    def is_lottery_message(self) -> bool:
        img_src_text = ''
        full_desc_text = ''
        try:
            images = self.web_element.find_element_by_class_name(LotteryMessage.embed_description_element_class_name).find_elements_by_tag_name('img')
            if len(images) == 1:
                img_src_text = images[0].get_property('src') #why does get_property work here but not other places??
                full_desc_text = self.web_element.find_element_by_class_name(LotteryMessage.embed_description_element_class_name).text
        except:
            return False
        return img_src_text == 'https://cdn.discordapp.com/emojis/469835869059153940.png?v=1' and 'Claims: #' in full_desc_text and 'Likes: #' in full_desc_text

    def __repr__(self):
        str_rep = \
            f'''MESSAGE OBJECT:
                    \tid - {self.id}
                    \tauthor - {self.author},
                    \tis_group_starter - {self.is_group_starter},
                    \tgroup_starter.id - {self.group_starter.id},
                    \tcontext_index - {self.context_index},
                    \tsubclass - {type(self).__name__},
                    \tcharacter - {self.character}
                    '''
        return str_rep
        

# %%

bot = HelperBot()

# %% notes

#keep a record of currently active people
    #data:
        # last message time
        # if they have used their roll
        # if they have used their claim
        #

#create a selector based on myanimelist?

#saved constants
search_chat = 'in:mudae-rolls'
jump_button = 'jumpButton-JkYoYK'
search_input_field = 'public-DraftStyleDefault-block'
search_message = 'hit-1fVM9e'
search_exit = 'icon-38sknP'
chat_section = 'messagesWrapper-1sRNjr'

#unused
time_stamp_element_selector = 'span.timestamp-3ZCmNB > span' # get aria-label property


#%%
#log this data somewhere

from threading import Thread
from time import time
from typing import Callable
from selenium.common.exceptions import TimeoutException

def send_and_await(message: str, bot: HelperBot, tries: int, sleep_time: float, is_response: Callable[[Message], bool]):
    for i in range(tries):
        returned_message: Message
        #print(i)
        returned_message = bot.send_message(message)
        #print('mine', returned_message)
        
        def found_response(driver):
            possible_responses = Message.get_context(driver)
            # i save the index because im worried that Message.get_context will be called outside of the thread (i fixed this so that only one thread can run it at a time)
            returned_message_index = returned_message.context_index
            if returned_message_index is not None: 
                possible_responses = possible_responses[:returned_message_index]
            for msg in possible_responses:
                #check if msg matches outline of the expected response
                if is_response(msg): #expected response was found
                    print(f'response found successfully after {i+1} attempts')
                    return True
            return False
        
        #await response
        try:
            WebDriverWait(bot.driver, timeout=sleep_time, poll_frequency=0.001).until(found_response)
            #success
            return
        except TimeoutException:
            if i+1 >= tries: #weird if condition but i think it makes sense
                raise TimeoutException(f'Response message was not found in {tries} attempts')

def interval_actions(bot: HelperBot):
    sleep(8)
    while True:
        start_time = time()
        send_and_await('$m', bot, tries=15, sleep_time=4, is_response=lambda m: isinstance(m, MudaeMessage) and m.content.startswith('{0}, the roulette is limited to'.format(bot.username.split('#')[0])))
        send_and_await('$p', bot, tries=3, sleep_time=10, is_response=lambda m: isinstance(m, MudaeMessage) and m.content.startswith('One try per interval of'))
        send_and_await('$dk', bot, tries=3, sleep_time=10, is_response=lambda m: isinstance(m, MudaeMessage) and m.content.startswith('Next $dk reset in'))
        end_time = time()
        time_delta = end_time - start_time
        sleep(3600-time_delta) #sleep for an hour

def start_loop():
    #bot.scroll_chat_down()
    Thread(target=interval_actions, args=[bot]).start()
    while True:
        new_msg = False
        for msg in Message.get_context(bot.driver):
            #print(msg)
            if msg.is_viewed:
                break
            elif isinstance(msg, LotteryMessage):
                msg: LotteryMessage
                if msg.is_married:
                    msg.click_reaction(bot)
                    print(' - '.join(['married', msg.character]))
                elif msg.value > 200:
                    msg.click_reaction(bot)
                    print(' - '.join(['I just married', msg.character]))
                else:
                    print(' - '.join(['not married', msg.character]))
            print(msg)
            new_msg = True           
            msg.is_viewed = True
        if new_msg:
            print('==== end of message chain ====')
        bot.scroll_chat_down()
    

if __name__ == '__main__':
    Message._context = [] # for jupyter server debugging
    try:
        start_loop()
    except StaleElementReferenceException as e:
        bot.driver.save_screenshot('debug.png')
        raise e
