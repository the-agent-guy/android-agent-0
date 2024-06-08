from android_controller import AndroidController
from gpt4o_agent import GPT4oAgent

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
            print(screenshot)
            actions = self.model(screenshot, self.task)
            for action in actions:
                self.controller.action_execute(action)
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
    model = GPT4oAgent()
    automaton = Automaton(controller, model)
    automaton.run_task(task)


if __name__ == "__main__":
    main()
