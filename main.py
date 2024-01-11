import os
import asyncio
import autogen
import panel as pn
from info import MyAccordion
import autogen


from ui_utils import AppUI

pn.extension(notifications=True)

msg_count = 0
specifications = {
    "description": "",
    "target_audience": "",
    "type_of_post": "",
    "tone_of_voice": "",
    "rag_prompt": ""
}

input_future = None

indicator = pn.indicators.LoadingSpinner(value=False, size=25, styles={'margin-left': '10.5rem'}) # load spinner
selected_post_text = None
is_post_selected = False
post_draft_initialized = False
initiate_chat_task_created = False
final_image_prompt = None
original_image_prompt = None
create_image_btn = pn.widgets.Button(name='Create Image', button_type='primary')
file_name = ""
file_input = pn.widgets.FileInput(accept='.csv,.json,.pdf,.txt,.md', name='Upload File', visible=False)
rag_selected = False

# AGENTS
linkedin_agent_temperature = 0.5
ragproxyagent = None
rag_assistant = None
user_proxy = None
linkedin_agent = None
linkedin_agent_name = None
critic_agent = None
critic_agent_name = None
seo_critic_agent = None
seo_critic_agent_name = None
image_agent = None
image_agent_name = None
groupchat = None
manager = None
avatar = None

def setup():
    main()
    
def main():

    def callback(contents: str, user: str, instance: pn.chat.ChatInterface):
        pass
    # MAIN COMPONENTS
  
    ui = AppUI()
    chat_interface1 = ui.get_twitter_chat()
    chat_interface1.disabled = False
    chat_interface1.send("Give a fist up my anus.", user="System", respond=False)
    # Chat buttons
    chat_interface1.show_rerun = False
    chat_interface1.show_undo = False
    chat_interface1.visible = False

    chat_interface2 = ui.get_linked_in_chat()
    chat_interface2.visible = False

    ### COMPONENT FUNCTIONS ###
    def activate_rag(event):
        global rag_selected
        rag_selected = not rag_selected
        file_input.visible = not file_input.visible
    
    def set_temperature(event):
        global linkedin_agent_temperature
        linkedin_agent_temperature = temp_slider.value
  
    def append_chat(env):
        chat_interface2.clear()
        chat_interface1.clear()
        if flow_selector.value == "LinkedIn":
            chat_interface2.visible = False
            chat_interface1.visible = True
        elif flow_selector.value == "Twitter":
            chat_interface1.visible = False
            chat_interface2.visible = True
            chat_interface2.send("Give a fist up my LinkedIN pippeli.", user="System", respond=False)

    flow_selector = pn.widgets.Select(options=['LinkedIn', 'Twitter', 'Instagram', 'Facebook', 'Web Page'], name='Target Platform')
    pn.bind(append_chat, flow_selector, watch=True)

    temp_slider = pn.widgets.FloatSlider(name='Creativity (0 low, 1 high)', start=0, end=1, value=0.5)
    pn.bind(set_temperature, temp_slider, watch=True)
    rag_switch = pn.widgets.Switch(name='Switch', align='center')
    pn.bind(activate_rag, rag_switch, watch=True)
    rag_switch_label = pn.pane.Markdown("Activate RAG Agent")
    labeled_switch = pn.Row(rag_switch_label, rag_switch)

    # FILE INPUT
    # delete all files in the folder first
    def delete_files(env=None):
        folder = './uploaded_files/'
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                file_input.disabled = False
                update_uploaded_files()
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    delete_files()

    file_column = pn.Column(width=300)
    def update_uploaded_files():
        file_column.clear()
        for filename in os.listdir('./uploaded_files/'):
            row = pn.Row()
            delete_btn =  pn.widgets.Button(name="Delete", button_type="danger")
            pn.bind(delete_files, delete_btn, watch=True)
            file = pn.widgets.StaticText(name="File", value=filename, align="center", max_width=230)
            row.append(file)
            row.append(delete_btn)
            file_column.append(row)

    update_uploaded_files()

    def save_file(event):
        global file_name
        file_name = file_input.filename # so the RAG agent can find it

        # check if file already exists in ./uploaded_files/, if so do not save it
        if os.path.exists(f"./uploaded_files/{file_name}"):
            pn.state.notifications.position = "top-center"
            pn.state.notifications.warning("File already exists!", duration=2500)
            file_input.value = None
            return

        print("Saving file...")
        uploaded_filename = file_input.filename
        file_byte_string = file_input.value
        save_path = './uploaded_files/'  # Replace with desired path

        os.makedirs(save_path, exist_ok=True)
        full_save_path = os.path.join(save_path, uploaded_filename)
        
        with open(full_save_path, 'wb') as file_to_write:
            file_to_write.write(file_byte_string)

        print(f'File "{uploaded_filename}" saved at "{full_save_path}"')
        pn.state.notifications.position = "top-center"
        pn.state.notifications.success("File uploaded successfully!", duration=2500)
        file_input.disabled = True
        update_uploaded_files()

    # Attach the save function to the value parameter
    file_input.param.watch(save_file, 'value')
    
    # Uploaded files
    uploaded_files_txt = pn.widgets.StaticText(name='Uploaded File', value='')
    
    # column = pn.Column('Settings', api_key_input, flow_selector, temp_slider, freq_slider, max_rounds_input, type_of_post_selector, target_audience_selector, file_input)
    column = pn.Column('Settings', flow_selector, temp_slider, labeled_switch, file_input, uploaded_files_txt, file_column)

    info_accordion = MyAccordion.get_accordion()

    logout = pn.widgets.Button(name="Log out")
    logout.js_on_click(code="""window.location.href = './logout'""")
    # PANEL
    template = pn.template.MaterialTemplate(
        title="iDA Autogen Chat",
        header=[info_accordion, indicator],
        sidebar=[logout, column],
        main=[chat_interface1, chat_interface2],
    )

    template.servable()
    # template.show()

if __name__ == "__main__":
    # main()
    setup()

setup()
