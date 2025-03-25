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
from kivy.lang import Builder
from typing import Dict, List, Optional

# После импортов и перед Builder.load_string добавим:

class StyledButton(Button):
    """Базовый класс для стилизованных кнопок с улучшенным внешним видом"""
    pass

class StyledSpinner(Spinner):
    """Базовый класс для стилизованных выпадающих списков"""
    pass

class StyledLabel(Label):
    """Базовый класс для стилизованных текстовых меток"""
    pass

class SectionLabel(Label):
    """Базовый класс для заголовков секций с особым форматированием"""
    pass

# Определяем стили в KV language
Builder.load_string('''
<StyledTextInput@TextInput>:
    background_color: (0.95, 0.95, 0.95, 1)
    foreground_color: (0.2, 0.2, 0.2, 1)
    cursor_color: (0.2, 0.6, 0.8, 1)
    font_size: '16sp'
    padding: [10, 10, 10, 10]
    size_hint_y: None
    height: 45
    canvas.before:
        Color:
            rgba: (0.8, 0.8, 0.8, 1)
        Line:
            rectangle: self.x, self.y, self.width, self.height
            width: 1.5

<StyledButton@Button>:
    background_color: (0.2, 0.6, 0.8, 1)
    color: (1, 1, 1, 1)
    size_hint_y: None
    height: 45
    font_size: '16sp'
    canvas.before:
        Color:
            rgba: (0.165, 0.494, 0.657, 1) if self.state == 'normal' else (0.145, 0.435, 0.580, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [5,]

<StyledSpinner@Spinner>:
    background_color: (0.9, 0.9, 0.9, 1)
    color: (0.2, 0.2, 0.2, 1)
    size_hint_y: None
    height: 45
    font_size: '16sp'
    canvas.before:
        Color:
            rgba: (0.8, 0.8, 0.8, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [5,]

<StyledLabel@Label>:
    color: (0.2, 0.2, 0.2, 1)  # Тёмный текст для контраста
    font_size: '16sp'
    bold: True
    size_hint_y: None
    height: 35
    text_size: self.size
    halign: 'left'
    valign: 'middle'
    canvas.before:
        Color:
            rgba: (0.9, 0.9, 0.9, 1)  # Светло-серый фон для метки
        Rectangle:
            pos: self.pos
            size: self.size

<SectionLabel@Label>:
    color: (0.2, 0.6, 0.8, 1)  # Голубой цвет для заголовков секций
    font_size: '18sp'
    bold: True
    size_hint_y: None
    height: 45
    canvas.before:
        Color:
            rgba: (0.95, 0.95, 0.95, 1)
        Rectangle:
            pos: self.pos
            size: self.size

<ReportGenerator>:
    canvas.before:
        Color:
            rgba: (1, 1, 1, 1)  # Белый фон
        Rectangle:
            pos: self.pos
            size: self.size
    
    BoxLayout:
        orientation: 'vertical'
        padding: [30, 30, 30, 30]
        spacing: 20

        Label:
            text: 'ГЕНЕРАТОР ОТЧЕТОВ ТЕРМООБРАБОТКИ'
            font_size: '20sp'
            bold: True
            color: (0.2, 0.6, 0.8, 1)
            size_hint_y: None
            height: 50
''')

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

class StyledFocusableTextInput(FocusableTextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0.95, 0.95, 0.95, 1)
        self.foreground_color = (0.2, 0.2, 0.2, 1)
        self.cursor_color = (0.2, 0.6, 0.8, 1)
        self.font_size = '16sp'
        self.padding = [10, 10, 10, 10]
        self.size_hint_y = None
        self.height = 45

class TimeInput(StyledFocusableTextInput):
    """
    Специализированное поле для ввода времени.
    Обеспечивает:
    - Автоматическое форматирование в формат ЧЧ:ММ
    - Валидацию вводимых значений
    - Ограничение часов (0-23) и минут (0-59)
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hint_text = 'ЧЧ:ММ'
        self.input_type = 'number'
        self.last_value = ''
        self.bind(text=self.on_text)

    def insert_text(self, substring, from_undo=False):
        """
        Обработка ввода текста с автоматическим форматированием.
        Добавляет двоеточие после ввода часов и проверяет корректность значений.
        """
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
    """
    Виджет календаря для выбора даты.
    Возможности:
    - Отображение текущего месяца
    - Навигация по месяцам
    - Выделение текущей даты
    - Выбор даты кликом
    """
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
        """Форматирует текст с названием месяца и годом"""
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

# В начале файла добавим константы
NORMS = {
    'Печь 1': {
        'цикл1': 510,  # 8:30 (в минутах)
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

MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
          'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

class ReportGenerator(BoxLayout):
    """
    Основной класс генератора отчетов.
    Функциональность:
    - Ввод даты через календарь
    - Выбор печи
    - Ввод времени для двух программ
    - Расчет отклонений от нормативов
    - Генерация отчета в формате Markdown
    """
    def __init__(self, **kwargs):
        """Инициализация интерфейса и всех компонентов формы"""
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 30
        self.spacing = 20
        
        # Создаем основной контейнер с белым фоном и тенью
        main_container = BoxLayout(
            orientation='vertical',
            padding=30,
            spacing=20,
            size_hint_y=None
        )
        main_container.bind(minimum_height=main_container.setter('height'))
        
        # Нормативные значения (в минутах) для каждой печи
        self.norms = NORMS

        # Создаем список всех полей ввода в порядке навигации
        self.input_fields = []
        
        # Дата с календарем
        date_layout = BoxLayout(size_hint_y=None, height=40)
        self.date_input = StyledFocusableTextInput(
            hint_text='Дата (дд.мм.гггг)',
            multiline=False
        )
        date_button = StyledButton(
            text='📅',
            size_hint_x=None,
            width=40
        )
        date_button.bind(on_press=self.show_calendar)
        date_layout.add_widget(StyledLabel(
            text='Дата:',
            size_hint_x=0.3
        ))
        date_layout.add_widget(self.date_input)
        date_layout.add_widget(date_button)
        self.add_widget(date_layout)
        self.input_fields.append(self.date_input)
        
        # Номер печи
        furnace_layout = BoxLayout(size_hint_y=None, height=40)
        self.furnace_spinner = StyledSpinner(
            text='Печь 1',
            values=('Печь 1', 'Печь 2'),
            size_hint_x=0.7
        )
        furnace_layout.add_widget(StyledLabel(
            text='Печь:',
            size_hint_x=0.3
        ))
        furnace_layout.add_widget(self.furnace_spinner)
        self.add_widget(furnace_layout)
        self.input_fields.append(self.furnace_spinner)

        # Программа 1
        self.add_widget(SectionLabel(text='Программа 1'))
        
        prog1_start_layout = BoxLayout(size_hint_y=None, height=40)
        self.prog1_start = TimeInput()
        prog1_start_layout.add_widget(StyledLabel(
            text='Время включения:',
            size_hint_x=0.3
        ))
        prog1_start_layout.add_widget(self.prog1_start)
        self.add_widget(prog1_start_layout)
        self.input_fields.append(self.prog1_start)

        prog1_end_layout = BoxLayout(size_hint_y=None, height=40)
        self.prog1_end = TimeInput()
        prog1_end_layout.add_widget(StyledLabel(
            text='Время выключения:',
            size_hint_x=0.3
        ))
        prog1_end_layout.add_widget(self.prog1_end)
        self.add_widget(prog1_end_layout)
        self.input_fields.append(self.prog1_end)

        # Программа 2
        self.add_widget(SectionLabel(text='Программа 2'))
        
        prog2_start_layout = BoxLayout(size_hint_y=None, height=40)
        self.prog2_start = TimeInput()
        prog2_start_layout.add_widget(StyledLabel(
            text='Время включения:',
            size_hint_x=0.3
        ))
        prog2_start_layout.add_widget(self.prog2_start)
        self.add_widget(prog2_start_layout)
        self.input_fields.append(self.prog2_start)

        prog2_end_layout = BoxLayout(size_hint_y=None, height=40)
        self.prog2_end = TimeInput()
        prog2_end_layout.add_widget(StyledLabel(
            text='Время выключения:',
            size_hint_x=0.3
        ))
        prog2_end_layout.add_widget(self.prog2_end)
        self.add_widget(prog2_end_layout)
        self.input_fields.append(self.prog2_end)

        # Добавляем поле для уведомлений
        self.add_widget(SectionLabel(text='Уведомления'))
        self.notifications_input = StyledFocusableTextInput(
            hint_text='Введите уведомления',
            multiline=True,
            size_hint_y=None,
            height=100
        )
        self.add_widget(self.notifications_input)
        self.input_fields.append(self.notifications_input)

        # Привязываем обработчики событий навигации
        self.bind_navigation()

        # Обновляем кнопку генерации отчета
        generate_button = StyledButton(
            text='СГЕНЕРИРОВАТЬ ОТЧЕТ',
            size_hint_y=None,
            height=50,
            font_size='18sp',
            bold=True
        )
        generate_button.bind(on_press=self.generate_report)
        self.add_widget(generate_button)

    def calculate_time_difference(self, start_time, end_time):
        """
        Вычисляет разницу между временем начала и конца в минутах.
        Учитывает переход через полночь.
        """
        start = datetime.strptime(start_time, '%H:%M')
        end = datetime.strptime(end_time, '%H:%M')
        
        if end < start:
            end += timedelta(days=1)
            
        diff = end - start
        return diff.seconds // 60  # возвращаем разницу в минутах

    def calculate_deviation(self, actual, norm):
        """
        Вычисляет процентное отклонение от нормы.
        Положительное значение - превышение нормы
        Отрицательное значение - меньше нормы
        """
        deviation = ((actual - norm) / norm) * 100
        return deviation

    def format_time(self, minutes):
        """Форматирует минуты в строку ЧЧ:ММ"""
        try:
            hours, mins = divmod(minutes, 60)
            return f"{int(hours):02d}:{int(mins):02d}"
        except (TypeError, ValueError):
            return "00:00"

    def show_calendar(self, instance):
        """Показывает календарь для выбора даты"""
        try:
            content = CalendarWidget(callback=self.on_date_select)
            self.calendar_popup = Popup(
                title='Выберите дату',
                content=content,
                size_hint=(None, None),
                size=(400, 400)
            )
            self.calendar_popup.open()
        except Exception as e:
            self.show_error_popup(f"Ошибка при открытии календаря: {str(e)}")

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
        """
        Основной метод генерации отчета.
        Выполняет:
        1. Проверку заполнения всех полей
        2. Расчет времени этапов и отклонений
        3. Формирование отчета по шаблону
        4. Сохранение в файл
        5. Очистку полей после успешной генерации
        """
        try:
            # Проверка заполнения всех полей
            if not all([self.date_input.text, self.prog1_start.text, self.prog1_end.text,
                       self.prog2_start.text, self.prog2_end.text]):
                raise ValueError("Пожалуйста, заполните все поля времени")

            # Проверка формата времени
            time_fields = [self.prog1_start.text, self.prog1_end.text,
                          self.prog2_start.text, self.prog2_end.text]
            for field in time_fields:
                if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', field):
                    raise ValueError("Неверный формат времени. Используйте ЧЧ:ММ")

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
                    **за**  **{self.date_input.text}**  
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
            self.show_success_popup()

        except ValueError as ve:
            self.show_error_popup(str(ve))
        except Exception as e:
            self.show_error_popup(f"Неожиданная ошибка: {str(e)}")

    def get_deviation_symbol(self, deviation):
        """Возвращает символ отклонения в зависимости от значения"""
        if deviation > 0:
            return "🔺"
        elif deviation < 0:
            return "🔻"
        return "❎"

    def show_error_popup(self, message):
        """Показывает всплывающее окно с ошибкой"""
        popup = Popup(
            title='Ошибка',
            content=Label(text=message),
            size_hint=(None, None),
            size=(400, 200)
        )
        popup.open()

    def show_success_popup(self):
        """Показывает всплывающее окно об успехе"""
        popup = Popup(
            title='Успех',
            content=Label(text='Отчет успешно сгенерирован'),
            size_hint=(None, None),
            size=(300, 150)
        )
        popup.open()

    def bind_navigation(self):
        """
        Настройка навигации по полям ввода.
        Позволяет перемещаться между полями с помощью:
        - Стрелок вверх/вниз
        - Клавиши Enter
        """
        for i, field in enumerate(self.input_fields):
            field.bind(
                on_up=lambda x, idx=i: self.focus_previous_field(idx),
                on_down=lambda x, idx=i: self.focus_next_field(idx),
                on_text_validate=lambda x, idx=i: self.focus_next_field(idx)
            )

class ReportApp(App):
    """Основной класс приложения"""
    def build(self):
        # Устанавливаем размер окна
        Window.size = (600, 800)  # Ширина: 800, Высота: 900
        return ReportGenerator()

if __name__ == '__main__':
    ReportApp().run() 