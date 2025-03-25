from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from datetime import datetime, timedelta
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
import calendar
import re
from kivy.core.window import Window
from kivy.uix.widget import Widget

class FocusableWidget:
    """Миксин для добавления навигации по полям"""
    def __init__(self):
        self.register_event_type('on_tab')
        self.register_event_type('on_shift_tab')
        self.register_event_type('on_up')
        self.register_event_type('on_down')

    def on_tab(self):
        pass

    def on_shift_tab(self):
        pass

    def on_up(self):
        pass

    def on_down(self):
        pass

class FocusableTextInput(TextInput, FocusableWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        FocusableWidget.__init__(self)
        self.multiline = False
        self.write_tab = False

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        key, key_str = keycode
        if key_str == 'up':
            self.dispatch('on_up')
            return True
        elif key_str == 'down':
            self.dispatch('on_down')
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)

class TimeInput(FocusableTextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline = False
        self.hint_text = 'ЧЧ:ММ'
        self.input_type = 'number'
        self.last_value = ''
        self.bind(text=self.on_text)

    def insert_text(self, substring, from_undo=False):
        # Проверяем, что вводятся только цифры
        if not substring.isdigit():
            return
        
        # Получаем текущий текст и позицию курсора
        text = self.text
        cursor_pos = self.cursor[0]
        
        # Формируем новый текст
        new_text = text[:cursor_pos] + substring + text[cursor_pos:]
        
        # Проверяем формат времени
        if len(new_text) > 5:
            return
        
        # Автоматически добавляем двоеточие после часов
        if len(new_text) == 2:
            if 0 <= int(new_text) <= 23:
                new_text += ':'
                substring = substring + ':'
            else:
                new_text = '23:'
                substring = '23:'
        
        # Проверяем минуты
        if len(new_text) == 5:
            hours, minutes = new_text.split(':')
            if int(minutes) > 59:
                new_text = f"{hours}:59"
                substring = new_text[cursor_pos:]
        
        super().insert_text(substring, from_undo)

    def on_text(self, instance, value):
        # Сохраняем последнее корректное значение
        if value and ':' in value:
            try:
                hours, minutes = value.split(':')
                if hours.isdigit() and minutes.isdigit():
                    if 0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59:
                        self.last_value = value
            except ValueError:
                pass

class CalendarWidget(GridLayout):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.cols = 7
        self.callback = callback
        self.current_date = datetime.now()
        
        # Создаем основной layout
        self.main_layout = BoxLayout(orientation='vertical')
        
        # Создаем панель навигации
        nav_layout = BoxLayout(size_hint_y=None, height=40)
        
        # Кнопки для переключения месяцев
        self.prev_month = Button(text='<', size_hint_x=None, width=40)
        self.next_month = Button(text='>', size_hint_x=None, width=40)
        
        # Метка с текущим месяцем и годом
        self.month_year_label = Label(text=self.get_month_year_text())
        
        # Добавляем элементы в панель навигации
        nav_layout.add_widget(self.prev_month)
        nav_layout.add_widget(self.month_year_label)
        nav_layout.add_widget(self.next_month)
        
        # Привязываем обработчики к кнопкам
        self.prev_month.bind(on_press=self.previous_month)
        self.next_month.bind(on_press=self.next_month_handler)
        
        # Добавляем панель навигации в основной layout
        self.main_layout.add_widget(nav_layout)
        
        # Создаем grid для календаря
        self.calendar_grid = GridLayout(cols=7)
        self.create_calendar()
        self.main_layout.add_widget(self.calendar_grid)
        
        # Добавляем основной layout
        self.add_widget(self.main_layout)

    def get_month_year_text(self):
        """Возвращает текст с названием месяца и годом"""
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        return f"{months[self.current_date.month - 1]} {self.current_date.year}"

    def create_calendar(self):
        """Создает календарную сетку"""
        self.calendar_grid.clear_widgets()
        
        # Добавляем названия дней недели
        for day in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']:
            self.calendar_grid.add_widget(Label(text=day))
        
        # Получаем календарь на текущий месяц
        cal = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        
        for week in cal:
            for day in week:
                if day == 0:
                    # Пустая ячейка
                    self.calendar_grid.add_widget(Label(text=''))
                else:
                    # Создаем кнопку с днем
                    btn = Button(text=str(day))
                    btn.bind(on_press=lambda x, d=day: self.on_day_select(d))
                    # Выделяем текущий день
                    if (day == datetime.now().day and 
                        self.current_date.month == datetime.now().month and 
                        self.current_date.year == datetime.now().year):
                        btn.background_color = (0.5, 0.8, 0.5, 1)  # Зеленый для текущего дня
                    self.calendar_grid.add_widget(btn)

    def previous_month(self, instance):
        """Переключает на предыдущий месяц"""
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        
        self.month_year_label.text = self.get_month_year_text()
        self.create_calendar()

    def next_month_handler(self, instance):
        """Переключает на следующий месяц"""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        
        self.month_year_label.text = self.get_month_year_text()
        self.create_calendar()

    def on_day_select(self, day):
        """Обработчик выбора дня"""
        date = f"{day:02d}.{self.current_date.month:02d}.{self.current_date.year}"
        self.callback(date)

class ReportGenerator(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        
        # Нормативные значения (в минутах) для каждой печи
        self.norms = {
            'Печь 1': {
                'цикл1': 510,  # 8:30
                'цикл2': 210,  # 3:30
                'перерыв': 40,  # 0:40
                'общее': 760   # 12:40
            },
            'Печь 2': {
                'цикл1': 660,  # 11:00
                'цикл2': 210,  # 3:30
                'перерыв': 40,  # 0:40
                'общее': 910   # 15:10
            }
        }

        # Создаем список всех полей ввода в порядке навигации
        self.input_fields = []
        
        # Дата с календарем
        date_layout = BoxLayout(size_hint_y=None, height=40)
        self.date_input = FocusableTextInput(
            hint_text='Дата (дд.мм.гггг)',
            multiline=False
        )
        date_button = Button(
            text='📅',
            size_hint_x=None,
            width=40
        )
        date_button.bind(on_press=self.show_calendar)
        date_layout.add_widget(Label(text='Дата:', size_hint_x=0.3))
        date_layout.add_widget(self.date_input)
        date_layout.add_widget(date_button)
        self.add_widget(date_layout)
        self.input_fields.append(self.date_input)
        
        # Номер печи
        furnace_layout = BoxLayout(size_hint_y=None, height=40)
        self.furnace_spinner = Spinner(
            text='Печь 1',
            values=('Печь 1', 'Печь 2'),
            size_hint_x=0.7
        )
        furnace_layout.add_widget(Label(text='Печь:', size_hint_x=0.3))
        furnace_layout.add_widget(self.furnace_spinner)
        self.add_widget(furnace_layout)

        # Программа 1
        self.add_widget(Label(text='Программа 1'))
        
        prog1_start_layout = BoxLayout(size_hint_y=None, height=40)
        self.prog1_start = TimeInput()
        prog1_start_layout.add_widget(Label(text='Время включения:', size_hint_x=0.3))
        prog1_start_layout.add_widget(self.prog1_start)
        self.add_widget(prog1_start_layout)
        self.input_fields.append(self.prog1_start)

        prog1_end_layout = BoxLayout(size_hint_y=None, height=40)
        self.prog1_end = TimeInput()
        prog1_end_layout.add_widget(Label(text='Время выключения:', size_hint_x=0.3))
        prog1_end_layout.add_widget(self.prog1_end)
        self.add_widget(prog1_end_layout)
        self.input_fields.append(self.prog1_end)

        # Программа 2
        self.add_widget(Label(text='Программа 2'))
        
        prog2_start_layout = BoxLayout(size_hint_y=None, height=40)
        self.prog2_start = TimeInput()
        prog2_start_layout.add_widget(Label(text='Время включения:', size_hint_x=0.3))
        prog2_start_layout.add_widget(self.prog2_start)
        self.add_widget(prog2_start_layout)
        self.input_fields.append(self.prog2_start)

        prog2_end_layout = BoxLayout(size_hint_y=None, height=40)
        self.prog2_end = TimeInput()
        prog2_end_layout.add_widget(Label(text='Время выключения:', size_hint_x=0.3))
        prog2_end_layout.add_widget(self.prog2_end)
        self.add_widget(prog2_end_layout)
        self.input_fields.append(self.prog2_end)

        # Добавляем поле для уведомлений
        self.add_widget(Label(text='Уведомления'))
        self.notifications_input = FocusableTextInput(
            hint_text='Введите уведомления',
            multiline=True,
            size_hint_y=None,
            height=100
        )
        self.add_widget(self.notifications_input)
        self.input_fields.append(self.notifications_input)

        # Привязываем обработчики событий навигации
        for i, field in enumerate(self.input_fields):
            field.bind(
                on_up=lambda x, idx=i: self.focus_previous_field(idx),
                on_down=lambda x, idx=i: self.focus_next_field(idx)
            )

        # Кнопка генерации отчета
        self.add_widget(Button(
            text='Сгенерировать отчет',
            size_hint_y=None,
            height=50,
            on_press=self.generate_report
        ))

    def calculate_time_difference(self, start_time, end_time):
        """Вычисляет разницу между временем начала и конца"""
        start = datetime.strptime(start_time, '%H:%M')
        end = datetime.strptime(end_time, '%H:%M')
        
        if end < start:
            end += timedelta(days=1)
            
        diff = end - start
        return diff.seconds // 60  # возвращаем разницу в минутах

    def calculate_deviation(self, actual, norm):
        """Вычисляет отклонение от нормы в процентах"""
        deviation = ((actual - norm) / norm) * 100
        return deviation

    def format_time(self, minutes):
        """Форматирует минуты в строку ЧЧ:ММ"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    def show_calendar(self, instance):
        content = CalendarWidget(callback=self.on_date_select)
        self.calendar_popup = Popup(
            title='Выберите дату',
            content=content,
            size_hint=(None, None),
            size=(400, 400)
        )
        self.calendar_popup.open()

    def on_date_select(self, date):
        self.date_input.text = date
        self.calendar_popup.dismiss()

    def focus_next_field(self, current_idx):
        """Переход к следующему полю"""
        next_idx = (current_idx + 1) % len(self.input_fields)
        self.input_fields[next_idx].focus = True

    def focus_previous_field(self, current_idx):
        """Переход к предыдущему полю"""
        prev_idx = (current_idx - 1) % len(self.input_fields)
        self.input_fields[prev_idx].focus = True

    def clear_fields(self):
        """Очистка всех полей ввода"""
        for field in self.input_fields:
            field.text = ''
        self.furnace_spinner.text = 'Печь 1'

    def generate_report(self, instance):
        try:
            # Получаем нормативы для выбранной печи
            current_norms = self.norms[self.furnace_spinner.text]
            
            # Рассчитываем времена программ
            program1_time = self.calculate_time_difference(
                self.prog1_start.text,
                self.prog1_end.text
            )
            
            program2_time = self.calculate_time_difference(
                self.prog2_start.text,
                self.prog2_end.text
            )
            
            # Рассчитываем этапы и перерыв
            stage1_time = program1_time  # Этап 1 соответствует времени Программы 1
            stage2_time = program2_time  # Этап 2 соответствует времени Программы 2
            
            # Рассчитываем перерыв как разницу между концом Программы 1 и началом Программы 2
            break_time = self.calculate_time_difference(
                self.prog1_end.text,
                self.prog2_start.text
            )
            
            # Общее время - сумма всех этапов и перерыва
            total_time = stage1_time + stage2_time + break_time

            # Вычисляем отклонения
            stage1_dev = self.calculate_deviation(stage1_time, current_norms['цикл1'])
            stage2_dev = self.calculate_deviation(stage2_time, current_norms['цикл2'])
            break_dev = self.calculate_deviation(break_time, current_norms['перерыв'])
            total_dev = self.calculate_deviation(total_time, current_norms['общее'])

            # Обновляем шаблон отчета, добавляя пользовательские уведомления
            notifications = self.notifications_input.text.strip()
            if not notifications:
                notifications = "Всё отработало в штатном режиме"

            # Формируем отчет
            report_template = f"""🔥 **ИНФОРМАЦИЯ ПО ТЕРМООБРАБОТКЕ** 🔥  
                    **за** 📅 **{self.date_input.text}**  
🏭 **Литейный цех | Ответственный: Федотов А.А.**
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬  
🔘 **{self.furnace_spinner.text}** | 📶 **Статус: Активна**
┌───────────────┬───────────────┐  
│ **Программа 1**              │ **Программа 2**             │  
├───────────────┼───────────────┤  
│ 🕖 ВКЛ: `{self.prog1_start.text}`           │ 🕖 ВКЛ: `{self.prog2_start.text}`          │  
│ 🕚 ВЫКЛ: `{self.prog1_end.text}`        │ 🕚 ВЫКЛ: `{self.prog2_end.text}`       │  
└───────────────┴───────────────┘  
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬  
📊 **АНАЛИТИКА**
• 🟢 Этап 1: `{self.format_time(stage1_time)}` ({self.get_deviation_symbol(stage1_dev)} **{stage1_dev:.2f}%** от установленной **нормы**)  
• 🟡 Этап 2: `{self.format_time(stage2_time)}` ({self.get_deviation_symbol(stage2_dev)} **{stage2_dev:.2f}%** от установленной **нормы**)  
• ⏸️ Перерыв: `{self.format_time(break_time)}`  ({self.get_deviation_symbol(break_dev)} **{break_dev:.2f}%** от установленной **нормы**)
• 📌 **Общее время: {self.format_time(total_time)}** ({self.get_deviation_symbol(total_dev)} **{total_dev:.2f}%** от установленной **нормы**)
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬  
🚨 **УВЕДОМЛЕНИЯ**
⚠️ **{notifications}**
✅ **`Термообработка: ▰▰▰▰ 100%`**
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"""

            # Сохраняем отчет в файл
            with open(f'Отчет_{self.date_input.text.replace(".", "_")}.md', 'w', encoding='utf-8') as f:
                f.write(report_template)

            # Очищаем поля после успешной генерации отчета
            self.clear_fields()
            
            # Показываем сообщение об успешной генерации
            popup = Popup(
                title='Успех',
                content=Label(text='Отчет успешно сгенерирован'),
                size_hint=(None, None),
                size=(300, 150)
            )
            popup.open()

        except Exception as e:
            # Показываем сообщение об ошибке
            popup = Popup(
                title='Ошибка',
                content=Label(text=f'Ошибка при генерации отчета:\n{str(e)}'),
                size_hint=(None, None),
                size=(400, 200)
            )
            popup.open()

    def get_deviation_symbol(self, deviation):
        """Возвращает символ отклонения в зависимости от значения"""
        if deviation > 0:
            return "🔺"
        elif deviation < 0:
            return "🔻"
        return "❎"

class ReportApp(App):
    def build(self):
        return ReportGenerator()

if __name__ == '__main__':
    ReportApp().run() 