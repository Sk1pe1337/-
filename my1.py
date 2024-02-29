import tkinter as tk
from tkinter import filedialog, colorchooser, simpledialog
from PIL import Image, ImageDraw, ImageTk, ImageFont


class PaintApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Редактор Изображений")
        self.root.config(cursor="pencil")
        root.state('zoomed')

        self.current_color = 'black'
        self.brush_size = 5
        self.eraser_size = 20
        self.current_tool = 'кисть'

        self.canvas_width = 1920
        self.canvas_height = 1080
        self.c = tk.Canvas(self.root, bg='white', width=self.canvas_width, height=self.canvas_height)
        self.setup_menu()
        self.setup_color_palette()
        self.setup_tool_menu()
        self.setup_bindings()
        self.image_bounds = (0, 0, self.canvas_width, self.canvas_height)

        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.history = [self.image.copy()]
        self.shapes = []
        self.setup_zoom_bindings()
        self.canvas_image = None
        self.c.pack(fill=tk.BOTH, expand=True)
        self.update_canvas()
        # Для функциональности обрезки
        self.selecting = False
        self.start_x = None
        self.start_y = None
        self.rect = None

        # Для функциональности перемещения
        self.moving = False
        self.move_start_x = None
        self.move_start_y = None
        self.image_position = (0, 0)

    # это все бинды
    def setup_bindings(self):
        self.root.bind('<FocusIn>', self.set_focus)
        self.c.bind('<Button-1>', self.handle_click)
        self.c.bind('<B1-Motion>', self.handle_motion)
        self.c.bind('<ButtonRelease-1>', self.handle_release)
        self.c.bind('<Shift-Button-1>', self.start_crop)
        self.c.bind('<Shift-B1-Motion>', self.do_crop)
        self.c.bind('<Shift-ButtonRelease-1>', self.end_crop)
        self.c.bind('<Shift-Button-2>', self.start_move)
        self.c.bind('<Shift-B2-Motion>', self.move_image)
        self.c.bind('<Shift-ButtonRelease-2>', self.end_move)
        self.c.bind('<Control-Button-1>', self.start_fill)
        self.root.bind('<Control-Key-z>', self.undo)
        self.root.bind('<Control-s>', self.save_image)
        self.root.bind('<Control-S>', self.save_image)
        self.root.bind('<Control-n>', self.load_image)
        self.root.bind('<Control-N>', self.load_image)
        self.root.bind('<Control-Alt-s>', self.resize_image)
        self.root.bind('<Control-Alt-S>', self.resize_image)
        self.root.bind('<Control-Alt-g>', self.flip_horizontal)
        self.root.bind('<Control-Alt-G>', self.flip_horizontal)
        self.root.bind('<Control-Shift-M>', self.apply_bw_filter)
        self.root.bind('<Control-Shift-m>', self.apply_bw_filter)
        self.root.bind('<Control-Shift-J>', lambda event: self.select_tool("crop"))
        self.root.bind('<Control-Shift-K>', lambda event: self.select_tool("доливка"))
#холс по умолчанию
    def expand_canvas(self, new_width, new_height):
        self.c.config(width=new_width, height=new_height)
        new_image = Image.new("RGB", (new_width, new_height), "white")

        new_image.paste(self.image, (0, 0))

        self.image = new_image
        self.draw = ImageDraw.Draw(self.image)

        self.update_canvas()
#для золста что бы менять размер
    def prompt_expand_canvas(self):
        new_width = simpledialog.askinteger("Новая ширина", "Введите новую ширину холста:")
        new_height = simpledialog.askinteger("Новая высота", "Введите новую высоту холста:")
        if new_width and new_height:
            self.expand_canvas(new_width, new_height)

    # бинд для зума
    def setup_zoom_bindings(self):
        self.c.bind('<MouseWheel>', self.zoom_image)

    def handle_click(self, event):
        if self.current_tool == 'доливка':
            self.start_fill(event)
        elif self.current_tool in ['кисть', 'ластик']:
            self.start_paint(event)
            self.save_to_history()
        elif self.current_tool in ['rectangle', 'oval', 'line']:
            self.start_draw_shape(event)
        elif self.current_tool == "text":
            self.add_text(event)
        elif self.current_tool == 'fill':
            self.start_fill(event)
#это что бы можно было рисовать по ЛКМ
    def handle_motion(self, event):
        if self.current_tool in ['кисть', 'ластик']:
            self.do_paint(event)
        elif self.current_tool in ['rectangle', 'oval', 'line']:
            self.update_draw_shape(event)
#доп фигурки
    def handle_release(self, event):
        if self.current_tool in ['rectangle', 'oval', 'line', 'кисть', 'ластик']:
            self.finalize_draw_shape(event)
        self.painting_started = False  # Сброс флага рисования
        self.save_to_history()

    # root focus
    def set_focus(self, event):
        self.root.focus_set()

    # fuction for zoom
    def zoom_image(self, event):
        scale_factor = 1.1
        if event.num == 5 or event.delta == -120: 
            scale_factor = 1.0 / scale_factor
        x, y = self.c.canvasx(event.x), self.c.canvasy(event.y)  
        new_width = int(self.image.width * scale_factor)
        new_height = int(self.image.height * scale_factor)
        self.image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.draw = ImageDraw.Draw(self.image)

        self.save_to_history()

        self.update_canvas()

    # all menu
    def setup_menu(self):
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)

        file_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Файл", menu=file_menu, )
        file_menu.add_command(label="Сохранить", accelerator="Ctrl+S", command=self.save_image_as)

        file_menu.add_command(label="Загрузить изображение", accelerator="Ctrl+N", command=self.load_image)

        edit_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Редактировать", menu=edit_menu)
        edit_menu.add_command(label="Изменить размер", accelerator="Ctrl+Alt+S", command=self.resize_image)

        # Подменю для вращения
        self.rotate_menu = tk.Menu(edit_menu, tearoff=0)
        self.rotate_menu.add_command(label="По часовой стрелке", command=self.rotate_clockwise)
        self.rotate_menu.add_command(label="Против часовой стрелки", command=self.rotate_counterclockwise)
        edit_menu.add_cascade(label="Вращение", menu=self.rotate_menu)

        edit_menu.add_command(label="Отразить по горизонтали", accelerator="Ctrl+Alt+G", command=self.flip_horizontal)
        edit_menu.add_command(label="Черно-белый фильтр", accelerator="Ctrl+Shift+M", command=self.apply_bw_filter)
        edit_menu.add_command(label="Обрезать", accelerator="Ctrl+Shift+J", command=lambda: self.select_tool("crop"))

        edit_menu.add_command(label="Расширить холст", command=self.prompt_expand_canvas)

    # panel color
    def setup_color_palette(self):
        self.color_palette_frame = tk.Frame(self.root, width=60)
        self.color_palette_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        colors = ['black', 'gray', 'white', 'red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet']
        for color in colors:
            btn = tk.Button(self.color_palette_frame, bg=color, width=2, height=1,command=lambda color=color: self.select_color(color))
            btn.pack(pady=2)

    # tools
    def setup_tool_menu(self):
        self.tool_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Инструменты", menu=self.tool_menu)
        self.tool_menu.add_command(label="Кисть", command=lambda: self.select_tool("кисть"))
        self.tool_menu.add_command(label="Ластик", command=lambda: self.select_tool("ластик"))
        self.tool_menu.add_command(label="Заливка", command=lambda: self.select_tool("fill"))
        self.tool_menu.add_command(label="Выбрать цвет", command=self.choose_color_from_dialog)
        self.tool_menu.add_command(label="Прямоугольник", command=lambda: self.select_tool("rectangle"))
        self.tool_menu.add_command(label="Овал", command=lambda: self.select_tool("oval"))
        self.tool_menu.add_command(label="Линия", command=lambda: self.select_tool("line"))
        self.tool_menu.add_command(label="Текст", command=lambda: self.select_tool("text"))
        self.tool_menu.add_command(label="Заливка всего холста", command=lambda: self.select_tool("fill_canvas"))

    # color select
    def select_color(self, color):
        self.current_color = color

    # tool кист ластик и т д
    def select_tool(self, tool, ):
        self.current_tool = tool
        if tool == "кисть" or tool == "ластик":
            self.c.config(cursor="pencil" if tool == "кисть" else "circle")
            self.brush_size = 5 if tool == "кисть" else self.eraser_size
        elif tool == "crop":
            self.c.config(cursor="cross")
        elif tool == "доливка":
            self.c.config(cursor="dot")
        elif tool in ["rectangle", "oval", "line"]:
            self.c.config(cursor="crosshair")
        elif tool == "fill_canvas":
                self.fill_canvas_with_color(self.current_color)

    def start_draw_shape(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.current_tool == "rectangle":
            self.rect = self.c.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline=self.current_color)
        elif self.current_tool == "oval":
            self.rect = self.c.create_oval(self.start_x, self.start_y, event.x, event.y, outline=self.current_color)
        elif self.current_tool == "line":
            self.rect = self.c.create_line(self.start_x, self.start_y, event.x, event.y, fill=self.current_color)

    def update_draw_shape(self, event):
        if self.current_tool in ["rectangle", "oval", "line"]:
            self.c.coords(self.rect, self.start_x, self.start_y, event.x, event.y)
#закончить рисовать фигуру
    def finalize_draw_shape(self, event):
        if self.current_tool in ["rectangle", "oval"]:
            x0, y0, x1, y1 = self.c.coords(self.rect)
            if self.current_tool == "rectangle":
                self.draw.rectangle([x0, y0, x1, y1], outline=self.current_color)
            elif self.current_tool == "oval":
                self.draw.ellipse([x0, y0, x1, y1], outline=self.current_color)
        elif self.current_tool == "line":
            x0, y0, x1, y1 = self.c.coords(self.rect)
            self.draw.line([x0, y0, x1, y1], fill=self.current_color)
        self.save_to_history()

    def add_text(self, event):
        text = simpledialog.askstring("Текст", "Введите текст:")
        if text:
            font_size = simpledialog.askinteger("Размер шрифта", "Введите размер шрифта:", minvalue=1, maxvalue=100)
            if font_size:
                font_path = "C:\\Windows\\Fonts\\ARIALN.TTF"   
                font = ImageFont.truetype(font_path, font_size)
                self.draw.text((event.x, event.y), text, fill=self.current_color, font=font)
                self.update_canvas()
                self.save_to_history()

    # окно цветов
    def choose_color_from_dialog(self):
        chosen_color = colorchooser.askcolor(color=self.current_color)[1]
        if chosen_color:
            self.current_color = chosen_color
        self.current_color = colorchooser.askcolor(color=self.current_color)[1]


    def start_paint(self, event):
        if self.current_tool == 'доливка':
            self.start_fill(event)
        if self.current_tool == 'кисть':
            self.paint(event)
        elif self.current_tool == 'ластик':
            self.start_erase(event)


    def start_fill(self, event):
        x, y = event.x, event.y
        start_color = self.image.getpixel((x, y))
        self.flood_fill(x, y, self.current_color, start_color)
        self.update_canvas()
        self.save_to_history()
        self.fill_canvas_with_color(self.current_color)

   
    def get_pixel_color(self, x, y):
        image_x = self.image_position[0] + x
        image_y = self.image_position[1] + y
        return self.image.getpixel((image_x, image_y))

    # funtion zalivki
    def flood_fill(self, x, y, new_color, boundary_color):
        pixel_data = self.image.load()
        target_color = pixel_data[x, y]
        if target_color == boundary_color or target_color == new_color:
            return
        queue = [(x, y)]
        while queue:
            x, y = queue.pop(0)
            if pixel_data[x, y] == target_color:
                pixel_data[x, y] = new_color
                if x > 0: queue.append((x - 1, y))
                if x < self.image.width - 1: queue.append((x + 1, y))
                if y > 0: queue.append((x, y - 1))
                if y < self.image.height - 1: queue.append((x, y + 1))
        self.update_canvas()

    # lastik
    def start_erase(self, event):
        if self.current_tool == 'ластик':  # дописан
            self.erase(event)

    # lastik do
    def do_erase(self, event):  # Ластик
        if self.current_tool == 'ластик':  # дописан
            self.erase(event)

    # ластик
    def erase(self, event):  # функция ластика
        x1, y1 = (event.x - self.brush_size), (event.y - self.brush_size)
        x2, y2 = (event.x + self.brush_size), (event.y + self.brush_size)
        self.c.create_rectangle(x1, y1, x2, y2, fill="white", outline="white")
        self.draw.rectangle([x1, y1, x2, y2], fill="white", outline="white")
        self.update_canvas()

    # start paint
    def do_paint(self, event):
        if self.current_tool == 'кисть':
            self.save_to_history()
            self.paint(event)
        elif self.current_tool == 'ластик':  # дописан
            self.do_erase(event)
        elif not self.painting_started:
            self.save_to_history()
            self.painting_started = True  # Устанавливаем флаг начала рисования
        self.paint(event)
    # end paint
    def end_paint(self, event):
        if self.current_tool == 'кисть':
            self.save_to_history()

    # paint function
    def paint(self, event):
        if self.current_tool in ['кисть', 'ластик']:
            paint_color = 'white' if self.current_tool == 'ластик' else self.current_color
            x1, y1 = (event.x - self.brush_size), (event.y - self.brush_size)
            x2, y2 = (event.x + self.brush_size), (event.y + self.brush_size)
            corrected_x = event.x - self.image_position[0]
            corrected_y = event.y - self.image_position[1]
            self.c.create_oval(x1, y1, x2, y2, fill=paint_color, outline=paint_color)
            self.draw.ellipse([x1, y1, x2, y2], fill=paint_color, outline=paint_color)
            self.update_canvas()

    # save
    def save_to_history(self):
        self.history.append(self.image.copy())

    # ctrl z
    def undo(self, event=None):
        if len(self.history) > 1: 
            self.history.pop()  
            self.image = self.history[-1].copy() 
            self.update_canvas() 
        else:
            print("Нечего отменять")

    # ctrl s
    def save_image(self, event=None):
        file_path = filedialog.asksaveasfilename(defaultextension=".png")
        if file_path and self.image:
            self.image.save(file_path)

    # ctrk n
    def load_image(self, event=None):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.image = Image.open(file_path).convert("RGB")
            self.image = self.image.resize((self.canvas_width, self.canvas_height), Image.Resampling.LANCZOS)
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas()
            self.image_bounds = (0, 0, self.canvas_width, self.canvas_height)
            self.update_canvas()


    # move image
    def move_image(self, event):
        if self.moving:
            dx = event.x - self.move_start_x
            dy = event.y - self.move_start_y
            self.c.move(self.canvas_image, dx, dy)
            self.image_position = (self.image_position[0] + dx, self.image_position[1] + dy)
            self.move_start_x = event.x
            self.move_start_y = event.y

    # размер фото
    def resize_image(self, event=None):
        new_width = simpledialog.askinteger("Изменить размер", "Введите новую ширину:", parent=self.root)
        new_height = simpledialog.askinteger("Изменить размер", "Введите новую высоту:", parent=self.root)
        if new_width and new_height:
            self.save_to_history()
            self.image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.update_canvas()

    # развароты по часам
    def rotate_clockwise(self):
        self.save_to_history()
        self.image = self.image.rotate(-90, expand=True)
        self.update_canvas()

    # против часовой
    def rotate_counterclockwise(self):
        self.save_to_history()
        self.image = self.image.rotate(90, expand=True)
        self.update_canvas()

    # flip
    def flip_horizontal(self, event=None):
        self.save_to_history()
        self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
        self.update_canvas()

    # BW filters
    def apply_bw_filter(self, event=None):
        self.save_to_history()
        self.image = self.image.convert('L')
        self.update_canvas()

    # obrezka
    def start_crop(self, event):
        if self.current_tool != "crop":
            return
        self.selecting = True
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.c.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red")

    # delayet crop
    def do_crop(self, event=None):
        if not self.selecting or self.current_tool != "crop":
            return
        self.c.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    # end crop
    def end_crop(self, event):
        if not self.selecting or self.current_tool != "crop":
            return
        self.selecting = False
        bbox = self.c.coords(self.rect)
        self.c.delete(self.rect)
        self.crop_selection(bbox)

    # проверяет есть ли картинка в холсте
    def crop_selection(self, bbox):
        if not bbox or len(bbox) != 4 or not self.image:
            return
        x0, y0, x1, y1 = [int(coord) for coord in bbox]
        img_x0, img_y0, img_x1, img_y1 = self.image_bounds
        crop_x0, crop_y0 = max(x0, img_x0), max(y0, img_y0)
        crop_x1, crop_y1 = min(x1, img_x1), min(y1, img_y1)
        if crop_x1 > crop_x0 and crop_y1 > crop_y0:
            self.save_to_history()
            cropped_image = self.image.crop((crop_x0, crop_y0, crop_x1, crop_y1))
            self.image = cropped_image
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas()
            self.image_bounds = (0, 0, cropped_image.width, cropped_image.height)

    # start move
    def start_move(self, event):
        self.moving = True
        self.move_start_x = event.x
        self.move_start_y = event.y

    # двигаем
    def move_image(self, event):
        if self.moving and self.canvas_image is not None:
            dx = event.x - self.move_start_x
            dy = event.y - self.move_start_y
            self.c.move(self.canvas_image, dx, dy)
            self.image_position = (self.image_position[0] + dx, self.image_position[1] + dy)
            self.move_start_x = event.x
            self.move_start_y = event.y

    # end
    def end_move(self, event):
        self.moving = False

    # update холста
    def update_canvas(self):
        self.tk_image = ImageTk.PhotoImage(self.image)
        if self.canvas_image is None:
            self.canvas_image = self.c.create_image(0, 0, anchor="nw", image=self.tk_image)
        else:
            self.c.itemconfig(self.canvas_image, image=self.tk_image)
        self.c.pack(fill=tk.BOTH, expand=True)

    def fill_canvas_with_color(self, fill_color):
        new_image = Image.new("RGB", self.image.size, fill_color)
        self.image = new_image
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas()

    def fill_shape(self, shape_id, color):
        self.c.itemconfig(shape_id, fill=color)

    def save_image_as(self):
        file_types = [
            ('JPEG files', '*.jpeg;*.jpg'),
            ('PNG files', '*.png'),
            ('BMP files', '*.bmp'),
            ('GIF files', '*.gif'),
            ('TIFF files', '*.tiff;*.tif'),
        ]

        file_path = filedialog.asksaveasfilename(
            title="Save image as...",
            filetypes=file_types
        )

        if not file_path:
            return
        file_extension = file_path.split('.')[-1].lower()
        if file_extension not in ['jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff', 'tif']:
            file_path += '.png'  
            file_extension = 'png'

        file_format = 'JPEG' if file_extension in ['jpg', 'jpeg'] else file_extension.upper()
        if file_extension == 'tif':
            file_format = 'TIFF'

        try:
            self.image.save(file_path, file_format)
        except Exception as e:
            print(f"Ошибка сохранения файла: {e}")


root = tk.Tk()
paint_app = PaintApp(root)
root.mainloop()
