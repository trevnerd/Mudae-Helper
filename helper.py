#%%
from __future__ import annotations #fixes type checking for a class within itself
from selenium import webdriver
#from selenium.webdriver import WebDriver
from time import sleep
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
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


class HelperBot:
    """An object which helps interact with a 'standard' discord page - maybe rename from HelperBot"""
    #TODO: make more generally applicable to any discord use
    def __init__(self):
        self.text_field: WebElement

        self.driver = webdriver.Chrome()
        self.login()
        self.driver.get(secret.mudae_channel)
        sleep(5)
        self.text_field = self.driver.find_element_by_css_selector('#app-mount > div.app-1q1i1E > div > div.layers-3iHuyZ.layers-3q14ss > div > div > div > div.content-98HsJk > div.chat-3bRxxu > div > main > form > div > div > div > div > div.textArea-12jD-V.textAreaSlate-1ZzRVj.slateContainer-3Qkn2x > div.markup-2BOw-j.slateTextArea-1Mkdgw.fontSize16Padding-3Wk7zP > div')
        self.scroll_to_bottom()

    def login(self):
        self.driver.get('https://discord.com/login')
        self.driver.find_element_by_xpath('//*[@id="app-mount"]/div[2]/div/div[2]/div/div/form/div/div/div[1]/div[3]/div[1]/div/input').send_keys(secret.email)
        self.driver.find_element_by_xpath('//*[@id="app-mount"]/div[2]/div/div[2]/div/div/form/div/div/div[1]/div[3]/div[2]/div/input').send_keys(secret.pw)
        self.driver.find_element_by_xpath('//*[@id="app-mount"]/div[2]/div/div[2]/div/div/form/div/div/div[1]/div[3]/button[2]').click()
        sleep(5) #TODO: replace sleeps with proper wait conditions

    def send_message(self, text):
        self.text_field.send_keys(''.join(text, '\n'))
        sleep(5)
    
    def scroll_to_bottom(self): # doesn't completely work properly
        self.driver.find_element_by_class_name('public-DraftStyleDefault-block').send_keys('in:mudae-rolls\n')
        sleep(1)
        self.driver.find_element_by_class_name('hit-1fVM9e').find_element_by_class_name('header-23xsNx').click()
        self.driver.find_element_by_class_name('jumpButton-JkYoYK').click()
        self.driver.find_element_by_class_name('icon-38sknP').click()
        #press end key to scroll remainder of page
        self.driver.find_element_by_class_name('scroller-2LSbBU').click()
        #there must be a better way lol
        webdriver.ActionChains(self.driver).send_keys(Keys.END).perform()
        sleep(1)

class Message:
    """Wrapper for 'message' WebElements within the discord html"""
    _context: List[Message]
    _context = [] #holds messages based on what an associated HelperBot sees - in newest frist order
    
    #CONSTANTS
    message_element_class_name = 'message-2qnXI6'
    message_element_group_start_class_name = 'groupStart-23k01U' # a sepecial message element that is at the beginning of multiple messages from the same person
    author_element_class_name = 'username-1A8OIy'
    bot_verif_element_class_name = 'botText-1526X_'
    reactions_element_class_name = 'reaction-1hd86g' 

    def __init__(self, element: WebElement, context_index: int):
        self.web_element: WebElement
        self.web_element = element
        
        self._context_index: int
        self._context_index = context_index

        self.is_group_starter: bool
        try:
            self.is_group_starter = Message.message_element_group_start_class_name in self.web_element.get_attribute('class').split(' ')
        except StaleElementReferenceException:
            #TODO: find a better way to handel all stale web_elements
            print('stale element for some reason!')
            self.is_group_starter = None

        self._group_starter: Message
        if self.is_group_starter:
            self._group_starter = self
        else:
            self._group_starter = None

        self._author: str
        if self.is_group_starter:
            try:
                self._author = self.web_element.find_element_by_class_name(Message.author_element_class_name).text
            except NoSuchElementException:
                #can occur because of pinned messages
                self._author = 'Pin'
        else:
            self._author = 'Unknown'

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

    """
    def click_reaction(self, index: int, bot: HelperBot): #TODO: extend the functionality of reactions interactions
        try:
            reaction_elements = self.web_element.find_elements_by_class_name(Message.reactions_element_class_name)
            reaction_elements[i].click()
        except: #TODO: decide how to handel exceptions to warn of problem of IndexError and NoSuchElementException
            pass
    """

    @property
    def group_starter(self) -> Message:
        if self._group_starter is None:
            i = self.context_index+1
            while i < len(Message._context):
                if Message._context[i].is_group_starter:
                    self._group_starter = Message._context[i]
                i += 1
        return self._group_starter

    @property
    def author(self) -> str: #TODO: find more robust identifier than just a string
        if self.group_starter is not None:
            self._author = self.group_starter._author
        return self._author

    @property
    def is_from_bot(self):
        if self.group_starter is not None:
            self._is_from_bot = self.group_starter._is_from_bot
        return self._is_from_bot

    @property
    def context_index(self) -> int:
        return self._context_index
    
    @context_index.setter
    def context_index(self, index: int):
        self._context_index = index

    @staticmethod
    def get_context(bot: HelperBot) -> List[Message]: #TODO: split method up?
        web_elements: List[WebElement]
        web_elements = bot.driver.find_elements_by_class_name(Message.message_element_class_name)[::-1] #newest first order
        new_context: List[Message]
        new_context = []
        for i, web_element in enumerate(web_elements):
            new_message = Message(web_element, i)
            if new_message.is_from_bot: #TODO: generalize this subclass conversion process
                new_message = MudaeMessage(web_element, i)
                if LotteryMessage.is_lottery_message(new_message):
                    new_message = LotteryMessage(web_element, i)
            for old_message in Message._context:
                try:
                    if new_message == old_message:
                        Message.set_context(new_context)
                        return Message._context
                except StaleElementReferenceException:
                    #produce helpful info to get better fix
                    print(i, new_message, old_message)
                    Message._context = []
                    return Message.get_context(bot)
                    
            new_context.append(new_message) #appends by newest first
        Message.set_context(new_context)
        return Message._context
    
    @staticmethod
    def set_context(new_context: List[Message]):
        new_context = new_context + Message._context
        if len(new_context) >= 60:
            new_context = new_context[:60]
        for j, msg in enumerate(new_context):
            msg.context_index = j
        Message._context = new_context

    def __eq__(self, other: Message) -> bool:
        return self.web_element.get_property('id') == other.web_element.get_property('id')

class MudaeMessage(Message): #message from a bot (not necessarily Mudae) - TODO: make more robust to ensure message is from Mudae
    
    def __init__(self, element: WebElement, context_index: int):
        Message.__init__(self, element, context_index)

        assert self.is_from_bot, 'Message is not from a bot'

class LotteryMessage(MudaeMessage):
    #CONSTANTS
    character_name_element_class_name = 'embedAuthorName-3mnTWj'
    embed_description_element_class_name = 'embedDescription-1Cuq9a'
    message_footer_element_class_name = 'embedFooterText-28V_Wb'

    def __init__(self, element: WebElement, context_index: int):
        MudaeMessage.__init__(self, element, context_index)
        
        assert self.is_lottery_message(), 'This is not a LotteryMessage'

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
        #TODO: implement wait for reaction to appear (cause i know it will appear since it is a LotteryMessage)
        sleep(1)
        reaction_elements: List[WebElement]
        reaction_elements = self.web_element.find_elements_by_class_name(Message.reactions_element_class_name)
        reaction_start_state = 'reactionMe-wv5HKu' in reaction_elements[index].get_attribute('class')
        print(self.web_element.text)
        #NOTE: other elements on the page can block reactions - how do i get around this
        #      so that it always works??
        #      The problem seems to be the jump to bottom button getting in the way when the END key is pressed
        #       to fix i will just add a down arrow pess in the case of failure
        # this line seems to fix the issue
        #webdriver.ActionChains(bot.driver).move_to_element(reaction_elements[index]).click(reaction_elements[index])
        bot.driver.execute_script('arguments[0].click()', reaction_elements[index].find_element_by_class_name('reactionInner-15NvIl'))
        #TODO: maybe start using screenshots for debugging
        """
        try: 
            reaction_elements[index].click()
        except ElementClickInterceptedException:
            print('reaction click exception')
            bot.driver.find_element_by_class_name('scroller-2LSbBU').click()
            #there must be a better way lol
            webdriver.ActionChains(bot.driver).send_keys(Keys.ARROW_DOWN).perform()
            sleep(0.3)
            reaction_elements[index].click()
        """
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
        finally:
            return img_src_text == 'https://cdn.discordapp.com/emojis/469835869059153940.png?v=1' and 'Claims: #' in full_desc_text and 'Likes: #' in full_desc_text
        

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
Message._context = [] # for jupyter server debugging
if __name__ == '__main__':
    while True:
        for msg in Message.get_context(bot):
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
            msg.is_viewed = True
        bot.driver.find_element_by_class_name('scroller-2LSbBU').click()
        #there must be a better way lol
        webdriver.ActionChains(bot.driver).send_keys(Keys.END).perform()
        sleep(2)

#WebElement().location_once_scrolled_into_view
#%%
"""
reaction_elements: List[WebElement]
reaction_elements = Message.get_context(bot)[0].web_element.find_elements_by_class_name(Message.reactions_element_class_name)
print(reaction_elements[0])
bot.driver.execute_script('arguments[0].click();', reaction_elements[0].find_element_by_class_name('reactionInner-15NvIl'))
"""