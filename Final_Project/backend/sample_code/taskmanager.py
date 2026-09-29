# task_manager.py
# A simple, function-based CLI Task Manager

# Global list to hold our tasks
tasks = []

def show_menu():
    """Prints the main menu to the user."""
    print("\n--- TASK MANAGER ---")
    print("1. View Tasks")
    print("2. Add Task")
    print("3. Delete Task")
    print("4. Exit")

def view_tasks():
    """Loops through and displays all current tasks."""
    print("\n--- YOUR TASKS ---")
    if not tasks:
        print("No tasks found! Your schedule is clear. ")
    else:
        for index, task in enumerate(tasks, start=1):
            print(f"{index}. {task}")

def add_task():
    """Prompts user for a new task name and appends it to the global list."""
    new_task = input("\nEnter the task description: ").strip()
    if new_task:
        tasks.append(new_task)
        print(f"'{new_task}' has been added successfully.")
    else:
        print(" Task cannot be empty!")

def delete_task():
    """Displays tasks and deletes the one selected by the user index."""
    view_tasks()
    if not tasks:
        return
        
    try:
        task_num = int(input("\nEnter the number of the task to delete: "))
        if 1 <= task_num <= len(tasks):
            removed = tasks.pop(task_num - 1)
            print(f"'{removed}' has been deleted.")
        else:
            print(" Invalid task number.")
    except ValueError:
        print("Please enter a valid number.")

def main():
    """The core engine that runs the program loop."""
    while True:
        show_menu()
        choice = input("\nChoose an option (1-4): ").strip()
        
        if choice == "1":
            view_tasks()
        elif choice == "2":
            add_task()
        elif choice == "3":
            delete_task()
        elif choice == "4":
            print("\nGoodbye! Thanks for staying organized.")
            break
        else:
            print("Invalid choice. Please pick a number from 1 to 4.")

# This ensures the program only runs if executed directly
if __name__ == "__main__":
    main()