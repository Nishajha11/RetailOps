from tkinter import *
from PIL import Image, ImageTk
from tkinter import ttk, messagebox
import sqlite3
import os


class salesClass:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Inventory Management System | Developed by NDV")
        self.root.config(bg="white")
        self.root.focus_force()

        self.bill_list = []
        self.var_invoice = StringVar()

        # Title
        lbl_title = Label(self.root, text="View Customer Bill Details", font=("goudy old style", 30), bg="#184a45", fg="white", bd=3, relief=RIDGE)
        lbl_title.pack(side=TOP, fill=X, padx=10, pady=20)
        lbl_invoice = Label(self.root, text="Invoice No.", font=("times new roman", 15), bg="white").place(x=50, y=100)
        txt_invoice = Entry(self.root, textvariable=self.var_invoice, font=("times new roman", 15), bg="lightyellow").place(x=160, y=100, width=180, height=28)

        btn_search = Button(self.root, text="Search", command=self.search, font=("times new roman", 15, "bold"), bg="#2196f3", fg="white", cursor="hand2").place(x=360, y=100, width=120, height=28)
        btn_clear = Button(self.root, text="Clear", command=self.clear, font=("times new roman", 15, "bold"), bg="red", fg="white", cursor="hand2").place(x=490, y=100, width=120, height=28)

        # Bill List
        sales_Frame = Frame(self.root, bd=3, relief=RIDGE)
        sales_Frame.place(x=50, y=140, width=200, height=600)

        scrolly = Scrollbar(sales_Frame, orient=VERTICAL)
        self.Sales_List = Listbox(sales_Frame, font=("goudy old style", 15), bg="white", yscrollcommand=scrolly.set)
        scrolly.pack(side=RIGHT, fill=Y)
        scrolly.config(command=self.Sales_List.yview)
        self.Sales_List.pack(fill=BOTH, expand=1)
        self.Sales_List.bind("<<ButtonRelease-1>>", self.get_data)

        # Bill Area
        bill_Frame = Frame(self.root, bd=3, relief=RIDGE)
        bill_Frame.place(x=280, y=140, width=810, height=600)

        lbl_title = Label(bill_Frame, text="Customer Bill Area", font=("goudy old style", 20), bg="orange").pack(side=TOP, fill=X)

        scrolly2 = Scrollbar(bill_Frame, orient=VERTICAL)
        self.bill_area = Text(bill_Frame, font=("goudy old style", 15), bg="lightyellow", yscrollcommand=scrolly2.set)
        scrolly2.pack(side=RIGHT, fill=Y)
        scrolly2.config(command=self.bill_area.yview)
        self.bill_area.pack(fill=BOTH, expand=1)

        # Image
        self.bill_photo = Image.open("images/cat2.jpg")
        self.bill_photo = self.bill_photo.resize((350, 500), Image.LANCZOS)
        self.bill_photo = ImageTk.PhotoImage(self.bill_photo)

        lbl_image = Label(self.root, image=self.bill_photo, bd=0)
        lbl_image.place(x=1150, y=110)

        # Check for 'bill' directory
        self.ensure_bill_directory()

        # Display the bill list
        self.show()

    def ensure_bill_directory(self):
        bill_dir = 'bill'
        if not os.path.exists(bill_dir):
            os.makedirs(bill_dir)
            messagebox.showwarning("Warning", f"'{bill_dir}' directory did not exist. Created a new one.", parent=self.root)
        return bill_dir

    def show(self):
        self.bill_list = []
        self.Sales_List.delete(0, END)

        bill_dir = self.ensure_bill_directory()

        for file in os.listdir(bill_dir):
            if file.endswith('.txt'):
                self.Sales_List.insert(END, file)
                self.bill_list.append(file.split('.')[0])

    def get_data(self, event):
        index_ = self.Sales_List.curselection()
        if index_:
            file_name = self.Sales_List.get(index_)
            invoice_path = f"bill/{file_name}"

            self.bill_area.delete('1.0', END)
            with open(invoice_path, 'r') as fp:
                for line in fp:
                    self.bill_area.insert(END, line)

    def search(self):
        if self.var_invoice.get() == "":
            messagebox.showerror("Error", "Invoice no. should be required", parent=self.root)
        else:
            bill_dir = self.ensure_bill_directory()

            invoice_name = self.var_invoice.get()
            invoice_path = f"{bill_dir}/{invoice_name}.txt"

            if os.path.isfile(invoice_path):
                self.bill_area.delete('1.0', END)
                with open(invoice_path, 'r') as fp:
                    for line in fp:
                        self.bill_area.insert(END, line)
            else:
                messagebox.showerror("Error", f"Invalid Invoice no. or file '{invoice_path}' not found.", parent=self.root)

    def clear(self):
        self.show()
        self.bill_area.delete('1.0', END)


if __name__ == "__main__":
    root = Tk()
    obj = salesClass(root)
    root.mainloop()