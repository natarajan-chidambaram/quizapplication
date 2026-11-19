# The BAF (besser-agentic-framework) package is an optional runtime for this
# agent. The backend quiz app does not depend on it; importing this module
# without BAF installed must not break the app, so the import is guarded.
# When BAF IS installed the agent is wired exactly as generated before.
try:
    from baf.core.agent import Agent
    from baf.nlp.intent_classifier.intent_classifier_configuration import SimpleIntentClassifierConfiguration
    BAF_AVAILABLE = True
except ImportError:
    BAF_AVAILABLE = False
    Agent = None
    SimpleIntentClassifierConfiguration = None

import json
import logging
import operator
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

agent = None
if BAF_AVAILABLE:
    # Create the bot and load bot properties stored in a dedicated file
    agent = Agent('Library_Agent')
    agent.load_properties('config.yaml')

    # Define the platform your chatbot will use
    platform = agent.use_websocket_platform(use_ui=True)

    # WARNING: no LLM is configured, so this agent uses BAF's classical
    # intent classifier, which needs PyTorch (pip install besser-agentic-framework[torch]).
    ic_config = SimpleIntentClassifierConfiguration()
    agent.set_default_ic_config(ic_config)

    ##############################
    # INTENTS
    ##############################
    OpeningHours = agent.new_intent('OpeningHours', [
        'what are the opening hours?',
        'library hours',
        'when do you open?',
        'hours of operation',
        ],
        description='Asking for the opening hours of the library.'
    )
    CheapestBook = agent.new_intent('CheapestBook', [
        'how to get the title of the cheapest book of an author?',
        'I want to know the cheapest book',
        'which is the cheapest book?',
        ])
    Contact = agent.new_intent('Contact', [
        'I need to speak to someone',
        'contact support',
        'human assistance',
        ],
        description='Requesting to speak with a human assistant.'
    )
    Other = agent.new_intent('Other', [
        ],
        description='Any other question.'
    )


# RUN APPLICATION

if __name__ == '__main__':
    if agent is None:
        raise SystemExit(
            "besser-agentic-framework is not installed; the agent cannot run. "
            "Install it with: pip install besser-agentic-framework"
        )
    agent.run()
