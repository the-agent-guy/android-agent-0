from android_controller import AndroidController, list_devices
from gpt4o_naive_vision_agent import GPT4oNaiveVisionAgent
from gpt4o_vision_xml_elements_agent import GPT4oVisionXMLElementsAgent
import time

class Automaton:
    def __init__(self, controller, model):
        self.controller = controller
        self.model = model
        self.done = True

    def run_task(self, task):
        self.task = task
        self.done = False
        i = 0
        while not self.done:
            screenshot = self.controller.get_screenshot(i)
            xml = self.controller.get_xml(i)
            actions = self.model(screenshot, xml, self.task)
            for action in actions:
                self.controller.action_execute(action)
                time.sleep(2)
            i += 1


def main():

    devices = list_devices()
    assert len(devices) > 0
    if len(devices) == 1:
        device = devices[0]
    else:
        print("Devices: {} \nEnter ID to select Device: ".format(devices))
        device = input()

    print("Enter task to be performed: ")
    task = input()

    controller = AndroidController(device)
    # model = GPT4oNaiveVisionAgent()
    model = GPT4oVisionXMLElementsAgent()
    automaton = Automaton(controller, model)
    automaton.run_task(task)


if __name__ == "__main__":
    main()
