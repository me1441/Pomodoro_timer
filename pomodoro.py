"""
Таймер Pomodoro с задачами — GUI версия (tkinter)
"""

import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(Enum):
    """Статусы задачи"""
    PENDING = "⏳ В ожидании"
    IN_PROGRESS = "▶️ В работе"
    COMPLETED = "✅ Завершена"


@dataclass
class Task:
    """Класс задачи"""
    id: int
    name: str
    status: str
    created_at: str
    pomodoros: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Session:
    """Класс сессии"""
    task_id: int
    task_name: str
    start_time: str
    duration: int
    completed: bool
    
    def to_dict(self) -> dict:
        return asdict(self)


class PomodoroGUI:
    """Графический таймер Pomodoro"""
    
    POMODORO_TIME = 25
    BREAK_TIME = 5
    LONG_BREAK = 15
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🍅 Pomodoro Timer")
        self.root.geometry("500x700")
        self.root.resizable(False, False)
        self.root.configure(bg="#2c3e50")
        
        self.tasks: List[Task] = []
        self.sessions: List[Session] = []
        self.next_task_id = 1
        self.data_file = "pomodoro_data.json"
        
        self.timer_running = False
        self.current_seconds = 0
        self.timer_thread = None
        self.current_task = None
        
        self._create_styles()
        self._create_widgets()
        self._load_data()
        self._update_task_list()
    
    def _create_styles(self):
        """Настройка цветов"""
        self.bg = "#2c3e50"
        self.fg = "#ecf0f1"
        self.accent = "#e74c3c"  # Красный для помидора
        self.green = "#27ae60"
        self.blue = "#3498db"
        self.orange = "#e67e22"
    
    def _create_widgets(self):
        """Создание интерфейса"""
        # === Таймер (центр экрана) ===
        timer_frame = tk.Frame(self.root, bg=self.bg)
        timer_frame.pack(pady=20)
        
        self.timer_label = tk.Label(
            timer_frame,
            text="25:00",
            font=("Arial", 64, "bold"),
            bg=self.bg,
            fg=self.accent
        )
        self.timer_label.pack()
        
        self.status_label = tk.Label(
            timer_frame,
            text="Готов к работе",
            font=("Arial", 14),
            bg=self.bg,
            fg=self.fg
        )
        self.status_label.pack(pady=5)
        
        # === Прогресс бар ===
        self.progress = ttk.Progressbar(
            self.root,
            orient=tk.HORIZONTAL,
            length=400,
            mode='determinate',
            maximum=100
        )
        self.progress.pack(padx=20, pady=10)
        
        # === Кнопки управления таймером ===
        ctrl_frame = tk.Frame(self.root, bg=self.bg)
        ctrl_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            ctrl_frame,
            text="▶️ Старт",
            command=self._start_timer,
            bg=self.green,
            fg="white",
            font=("Arial", 12, "bold"),
            width=12,
            cursor="hand2",
            bd=0,
            pady=8
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = tk.Button(
            ctrl_frame,
            text="⏸️ Пауза",
            command=self._pause_timer,
            bg=self.orange,
            fg="white",
            font=("Arial", 12),
            width=12,
            cursor="hand2",
            bd=0,
            pady=8,
            state=tk.DISABLED
        )
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_btn = tk.Button(
            ctrl_frame,
            text="⏹️ Сброс",
            command=self._reset_timer,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 12),
            width=12,
            cursor="hand2",
            bd=0,
            pady=8
        )
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        
        # === Управление задачами ===
        task_frame = tk.LabelFrame(self.root, text=" Задачи ", 
                                  bg=self.bg, fg=self.fg,
                                  font=("Arial", 11, "bold"))
        task_frame.pack(padx=20, pady=10, fill=tk.X)
        
        # Ввод новой задачи
        input_frame = tk.Frame(task_frame, bg=self.bg)
        input_frame.pack(padx=5, pady=5, fill=tk.X)
        
        self.task_entry = tk.Entry(input_frame, font=("Arial", 12), width=30)
        self.task_entry.pack(side=tk.LEFT, padx=2)
        self.task_entry.bind('<Return>', lambda e: self._add_task())
        
        tk.Button(input_frame, text="➕ Добавить", command=self._add_task,
                 bg=self.blue, fg="white", font=("Arial", 10),
                 cursor="hand2", bd=0, pady=3).pack(side=tk.LEFT, padx=2)
        
        # Список задач
        list_frame = tk.Frame(task_frame, bg=self.bg)
        list_frame.pack(padx=5, pady=5, fill=tk.BOTH)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.task_listbox = tk.Listbox(
            list_frame,
            font=("Arial", 11),
            bg="#1a252f",
            fg=self.fg,
            selectbackground=self.blue,
            selectforeground="white",
            height=6,
            yscrollcommand=scrollbar.set
        )
        self.task_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.task_listbox.yview)
        
        # Кнопки задач
        task_btn_frame = tk.Frame(task_frame, bg=self.bg)
        task_btn_frame.pack(padx=5, pady=5, fill=tk.X)
        
        tk.Button(task_btn_frame, text="▶️ Выбрать", command=self._select_task,
                 bg=self.green, fg="white", font=("Arial", 10),
                 cursor="hand2", bd=0, pady=3).pack(side=tk.LEFT, padx=2)
        
        tk.Button(task_btn_frame, text="✅ Завершить", command=self._complete_task,
                 bg=self.blue, fg="white", font=("Arial", 10),
                 cursor="hand2", bd=0, pady=3).pack(side=tk.LEFT, padx=2)
        
        tk.Button(task_btn_frame, text="🗑️ Удалить", command=self._delete_task,
                 bg="#c0392b", fg="white", font=("Arial", 10),
                 cursor="hand2", bd=0, pady=3).pack(side=tk.LEFT, padx=2)
        
        # === Статистика ===
        stats_frame = tk.LabelFrame(self.root, text=" Статистика ", 
                                   bg=self.bg, fg=self.fg,
                                   font=("Arial", 11, "bold"))
        stats_frame.pack(padx=20, pady=10, fill=tk.X)
        
        self.stats_text = tk.Label(
            stats_frame,
            text="Помодоро сегодня: 0 | Всего: 0",
            font=("Arial", 11),
            bg=self.bg,
            fg=self.fg
        )
        self.stats_text.pack(pady=5)
        
        # === Кнопка сохранения ===
        tk.Button(self.root, text="💾 Сохранить и выйти", command=self._save_and_exit,
                 bg="#7f8c8d", fg="white", font=("Arial", 11),
                 cursor="hand2", bd=0, pady=8, width=20).pack(pady=10)
    
    def _add_task(self):
        """Добавление задачи"""
        name = self.task_entry.get().strip()
        if not name:
            messagebox.showwarning("Внимание", "Введите название задачи!")
            return
        
        task = Task(
            id=self.next_task_id,
            name=name,
            status=TaskStatus.PENDING.value,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            pomodoros=0
        )
        self.tasks.append(task)
        self.next_task_id += 1
        self.task_entry.delete(0, tk.END)
        self._update_task_list()
        self._save_data()
        messagebox.showinfo("Успех", f"Задача '{name}' добавлена!")
    
    def _update_task_list(self):
        """Обновление списка задач"""
        self.task_listbox.delete(0, tk.END)
        for task in self.tasks:
            status_icon = "⏳" if task.status == TaskStatus.PENDING.value else \
                         "▶️" if task.status == TaskStatus.IN_PROGRESS.value else "✅"
            self.task_listbox.insert(tk.END, 
                f"{status_icon} [{task.id}] {task.name} (🍅{task.pomodoros})")
    
    def _select_task(self):
        """Выбор задачи для помодоро"""
        selection = self.task_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите задачу из списка!")
            return
        
        idx = selection[0]
        self.current_task = self.tasks[idx]
        self.current_task.status = TaskStatus.IN_PROGRESS.value
        
        self.status_label.config(
            text=f"Задача: {self.current_task.name}",
            fg=self.blue
        )
        self._update_task_list()
        self._save_data()
        messagebox.showinfo("Задача выбрана", 
                           f"Запустите таймер для работы над задачой:\n'{self.current_task.name}'")
    
    def _complete_task(self):
        """Отметить задачу завершенной"""
        selection = self.task_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        self.tasks[idx].status = TaskStatus.COMPLETED.value
        self._update_task_list()
        self._save_data()
    
    def _delete_task(self):
        """Удалить задачу"""
        selection = self.task_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        task = self.tasks[idx]
        if messagebox.askyesno("Подтверждение", f"Удалить задачу '{task.name}'?"):
            self.tasks.pop(idx)
            self._update_task_list()
            self._save_data()
    
    def _start_timer(self):
        """Запуск таймера"""
        if not self.current_task:
            messagebox.showwarning("Внимание", "Сначала выберите задачу!")
            return
        
        if not self.timer_running:
            self.timer_running = True
            self.current_seconds = self.POMODORO_TIME * 60
            
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.status_label.config(text="🍅 Работа!", fg=self.accent)
            
            self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
            self.timer_thread.start()
    
    def _timer_loop(self):
        """Цикл таймера (в отдельном потоке)"""
        while self.timer_running and self.current_seconds > 0:
            mins, secs = divmod(self.current_seconds, 60)
            
            # Обновление интерфейса (через after для потокобезопасности)
            self.root.after(0, lambda m=mins, s=secs: 
                self.timer_label.config(text=f"{m:02d}:{s:02d}"))
            
            # Прогресс
            progress = ((self.POMODORO_TIME * 60 - self.current_seconds) / 
                       (self.POMODORO_TIME * 60)) * 100
            self.root.after(0, lambda p=progress: self.progress.config(value=p))
            
            time.sleep(1)
            self.current_seconds -= 1
        
        if self.timer_running and self.current_seconds <= 0:
            # Таймер завершен
            self.root.after(0, self._timer_complete)
    
    def _timer_complete(self):
        """Обработка завершения таймера"""
        self.timer_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        
        # Запись сессии
        if self.current_task:
            self.current_task.pomodoros += 1
            session = Session(
                task_id=self.current_task.id,
                task_name=self.current_task.name,
                start_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
                duration=self.POMODORO_TIME,
                completed=True
            )
            self.sessions.append(session)
            self._update_task_list()
            self._update_stats()
            self._save_data()
        
        # Сигнал
        self.status_label.config(text="✅ Помодоро завершено!", fg=self.green)
        self.timer_label.config(text="00:00")
        self.progress.config(value=100)
        
        # Предложение перерыва
        self._offer_break()
    
    def _offer_break(self):
        """Предложение перерыва"""
        if not self.current_task:
            return
        
        pomodoro_count = self.current_task.pomodoros
        if pomodoro_count % 4 == 0:
            break_time = self.LONG_BREAK
            msg = f"🎉 Длинный перерыв {break_time} мин!\n(4 помодоро завершено)"
        else:
            break_time = self.BREAK_TIME
            msg = f"☕ Короткий перерыв {break_time} мин!"
        
        if messagebox.askyesno("Перерыв", msg + "\n\nЗапустить таймер перерыва?"):
            self._start_break(break_time)
    
    def _start_break(self, minutes: int):
        """Запуск таймера перерыва"""
        self.current_seconds = minutes * 60
        self.timer_running = True
        self.status_label.config(text=f"☕ Перерыв {minutes} мин", fg=self.green)
        
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        
        self.timer_thread = threading.Thread(target=self._break_loop, daemon=True)
        self.timer_thread.start()
    
    def _break_loop(self):
        """Цикл перерыва"""
        while self.timer_running and self.current_seconds > 0:
            mins, secs = divmod(self.current_seconds, 60)
            self.root.after(0, lambda m=mins, s=secs: 
                self.timer_label.config(text=f"{m:02d}:{s:02d}"))
            time.sleep(1)
            self.current_seconds -= 1
        
        if self.timer_running:
            self.root.after(0, self._break_complete)
    
    def _break_complete(self):
        """Завершение перерыва"""
        self.timer_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.status_label.config(text="💪 Время работать!", fg=self.blue)
        self.timer_label.config(text="25:00")
        self.progress.config(value=0)
        messagebox.showinfo("Перерыв окончен", "Время вернуться к работе!")
    
    def _pause_timer(self):
        """Пауза таймера"""
        self.timer_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.status_label.config(text="⏸️ Пауза", fg=self.orange)
    
    def _reset_timer(self):
        """Сброс таймера"""
        self.timer_running = False
        self.current_seconds = 0
        self.timer_label.config(text="25:00")
        self.progress.config(value=0)
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Готов к работе", fg=self.fg)
    
    def _update_stats(self):
        """Обновление статистики"""
        today = datetime.now().strftime("%Y-%m-%d")
        today_count = sum(1 for s in self.sessions if s.start_time.startswith(today))
        total = len(self.sessions)
        self.stats_text.config(text=f"Помодоро сегодня: {today_count} | Всего: {total}")
    
    def _save_data(self):
        """Сохранение данных"""
        data = {
            "tasks": [t.to_dict() for t in self.tasks],
            "sessions": [s.to_dict() for s in self.sessions],
            "next_id": self.next_task_id
        }
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
    
    def _load_data(self):
        """Загрузка данных"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.tasks = [Task(**t) for t in data.get("tasks", [])]
                self.sessions = [Session(**s) for s in data.get("sessions", [])]
                self.next_task_id = data.get("next_id", 1)
                self._update_stats()
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    
    def _save_and_exit(self):
        """Сохранение и выход"""
        self._save_data()
        self.root.quit()


def main():
    root = tk.Tk()
    app = PomodoroGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()