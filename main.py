import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import pytesseract
from fpdf import FPDF

#esta clase es como tal la app
class conversor:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor de Imagenes a Texto")
        self.root.geometry("800x600")
        
        self.image_frame = tk.Frame(self.root)
        self.image_frame.pack(side=tk.LEFT, padx=20, pady=20)
        
        self.canvas = tk.Canvas(self.image_frame, width=600, height=400)
        self.canvas.pack()
        
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side=tk.RIGHT, padx=20, pady=20)
        
        self.load_button = tk.Button(self.button_frame, text="Cargar Imagen", bg="blue", fg="white", command=self.load_image)
        self.load_button.pack(pady=10, anchor=tk.N)
        
        self.extract_button = tk.Button(self.button_frame, text="Extraer Texto", bg="blue", fg="white", command=self.extract_text)
        self.extract_button.pack(pady=10, anchor=tk.N)
        
        self.pdf_button = tk.Button(self.button_frame, text="Guardar como PDF", bg="blue", fg="white", command=self.save_as_pdf)
        self.pdf_button.pack(pady=10, anchor=tk.N)
        
        self.img_label = tk.Label(self.image_frame)
        self.img_label.pack(pady=20)
        
        self.text_frame = tk.Frame(self.root)
        self.text_frame.pack(pady=20)
        
        self.scrollbar = tk.Scrollbar(self.text_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_box = tk.Text(self.text_frame, wrap=tk.WORD, yscrollcommand=self.scrollbar.set, padx=10, pady=10)
        self.text_box.pack(fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.text_box.yview)
        
        self.loaded_image = None
        self.detected_text = ""

#función para cargar la imagen del usuario
    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")])
        if file_path:
            self.loaded_image = Image.open(file_path)
            self.display_image(self.loaded_image)

#mostrar la imagen cargada en la pantalla
    def display_image(self, img):
        img.thumbnail((600, 400))
        img = ImageTk.PhotoImage(img)
        self.img_label.config(image=img)
        self.img_label.image = img

#se ocupa para guardar el texto como pdf, una vez extraído
    def save_as_pdf(self):
        if self.detected_text:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, self.detected_text)
            save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
            if save_path:
                pdf.output(save_path)
                messagebox.showinfo("PDF Guardado", "PDF guardado exitosamente.")
        else:
            messagebox.showwarning("Nada que guardar", "No hay texto para guardar como PDF.")

#primera función de PDI, preprocesamiento, se trata de la umbralización de la imagen para eliminar ruido y componentes no deseados
    def threshold_image(self, img, threshold=128):
        width, height = img.size
        thresholded_img = Image.new("L", (width, height))

        for x in range(width):
            for y in range(height):
                pixel = img.getpixel((x, y))
                if pixel < threshold:
                    thresholded_img.putpixel((x, y), 0)  # Negro
                else:
                    thresholded_img.putpixel((x, y), 255)  # Blanco

        return thresholded_img

#funcion de preprocesamiento para determinar si es necesario rotar la imagen, 
    def rotate_image(self, img):
        row_counts, col_counts = self.count_black_pixels(img)

        total_black_rows = sum(row_counts)
        total_black_cols = sum(col_counts)

        if total_black_cols > total_black_rows:
            width, height = img.size
            rotated_img = Image.new("L", (height, width))

            for x in range(width):
                for y in range(height):
                    rotated_img.putpixel((y, width - 1 - x), img.getpixel((x, y)))

            return rotated_img
        else:
            return img

#como se trata de una imagen pasada a escala de grises, se cuentan los pixeles "negros" para determinar donde empieza y termina una fila, renglón 
    def count_black_pixels(self, img):
        width, height = img.size
        row_counts = [0] * height
        col_counts = [0] * width

        for x in range(width):
            for y in range(height):
                if img.getpixel((x, y)) == 0:
                    row_counts[y] += 1
                    col_counts[x] += 1

        return row_counts, col_counts

#esta función se encargar de detectar los renglones de texto para enfocarse en ellos
    def detect_lines(self, img):
        row_counts, _ = self.count_black_pixels(img)
        height = len(row_counts)

        lines = []
        in_line = False
        start = 0

        for y in range(height):
            if row_counts[y] > 0 and not in_line:
                in_line = True
                start = y
            elif row_counts[y] == 0 and in_line:
                in_line = False
                end = y
                lines.append((start, end))

        if in_line:
            lines.append((start, height))

        return lines

#una de las funciones principales, segementa cada caracter ya procesado, para que posteriormente pueda ser comparado con el patrón y reconocido  
    def segment_characters(self, line_img):
        _, col_counts = self.count_black_pixels(line_img)
        width = len(col_counts)

        char_segments = []
        in_char = False
        start = 0

        for x in range(width):
            if col_counts[x] > 0 and not in_char:
                in_char = True
                start = x
            elif col_counts[x] == 0 and in_char:
                in_char = False
                end = x
                char_segments.append((start, end))
        if in_char:
            char_segments.append((start, width))

        return char_segments

#la función de la biblioteca tessreact SÓLO se utiliza como un "diccionario" de caracteres del español para que puedan compararse posteriormente, se utiliza para que el tiempo de ejecución sea óptimo y el programa evite confusiones
    def detect_text(self, img):
        text = pytesseract.image_to_string(img, lang='spa')  # Español
        return text
    

#para aplicar todos los procesos anteriore, se declara esta función, la cual aplica todo a la imagen cargada, subida por el usuario en la ventana
    def extract_text(self):
        if self.loaded_image:
            gray_img = self.loaded_image.convert("L") #convertir imagen en escala de grises
            thresholded_img = self.threshold_image(gray_img, threshold=128)
            corrected_img = self.rotate_image(thresholded_img)
            lines = self.detect_lines(corrected_img)

            self.detected_text = ""
            for i, (start, end) in enumerate(lines):
                line_img = corrected_img.crop((0, start, corrected_img.width, end))
                char_segments = self.segment_characters(line_img)

                for j, (char_start, char_end) in enumerate(char_segments):
                    char_img = line_img.crop((char_start, 0, char_end, line_img.height))

                    #la funcion de tessreact compara cada uno de los caracteres extraidos del segmentado con los de su "diccionario" y busca el que tenga la similitud con mayor "peso"
                    char_text = self.detect_text(char_img)
                    self.detected_text += char_text + " "

            self.text_box.delete(1.0, tk.END)  
            self.text_box.insert(tk.END, self.detected_text.strip())
        else:
            messagebox.showwarning("Error", "Carga una imagen primero.")
    

#funcion principal
def main():
    root = tk.Tk()
    app = conversor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
