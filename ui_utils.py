from twitter import TwitterChat
from linkedin import LinkedInChat
from document_wizard import DocumentWizard

class AppUI:

    general_template = None

    def __init__(self) -> None:
        self.linkedin = LinkedInChat()

    def paint_general_ui(self):
        pass

    def _paint_linked_in_ui(self):
        pass

    def get_twitter_chat(self):
        twitter = TwitterChat()
        return twitter.get_twitter_chat()

    def get_linked_in_chat(self, file_input, agent_temperature):
        return self.linkedin.get_linked_in_chat(file_input, agent_temperature)
    
    def set_rag(self, rag_selected):
        self.linkedin.set_rag(rag_selected)

    def get_document_wizard(self):
        document_wizard = DocumentWizard()
        return document_wizard.get_document_wizard_chat()
