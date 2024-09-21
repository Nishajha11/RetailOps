import re
from tkinter import *
import customtkinter
from PIL import Image, ImageTk
from tkinter import ttk, messagebox
import sqlite3


class supplierClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Supplier Record")
        self.root.geometry("1100x500+310+170")
        self.root.config(bg="#898AA6")

        ##-----All variables-----##

        self.var_emp_srchby = StringVar()
        self.var_sup_srchtxt = StringVar()

        self.var_sup_invoice = StringVar()
        self.var_sup_name = StringVar()
        self.var_sup_contact = StringVar()

        ##----Search Frame-----##
        ##---Combo box---##
        lbl_search = Label(self.root,text="Invoice No.",font=("goudy old style", 15), bg="#D3EBCD")
        lbl_search.place(x=900, y=90)

        txt_search = Entry(self.root, textvariable=self.var_sup_srchtxt, font=("goudy old style", 15),bg="lightyellow").place(x=1030, y=90,width=180)
        btn_search = Button(self.root, text="Search", command=self.Search, font=("goudy old style", 15),bg="lightblue", cursor="hand2").place(x=1220, y=90, width=120, height=34)

        ##----title----##
        lbl_title = Label(self.root, text="Supplier Details", font=("goudy old style",20, "bold"), bg="blue",fg="white").place(x=50, y=10,height=50, width=1270)

        ##------Content-----##
        ##-----row1--------##
        lbl_sup_invoice = Label(self.root, text="Invoice No.", font=("goudy old style", 15, "bold"), bg="#898AA6").place(x=50,y=90)
        txt_sup_invoice = Entry(self.root, textvariable=self.var_sup_invoice, font=("goudy old style", 15, "bold"),bg="lightyellow").place(x=210, y=90, width=220)

        ##----row2----##
        lbl_name = Label(self.root, text="Name", font=("goudy old style", 15, "bold"), bg="#898AA6").place(x=50, y=140)
        txt_name = Entry(self.root, textvariable=self.var_sup_name, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=210, y=140, width=220)

        ##----row3----##
        lbl_contact = Label(self.root, text="Contact", font=("goudy old style", 15, "bold"), bg="#898AA6").place(x=50,y=190)
        txt_contact = Entry(self.root, textvariable=self.var_sup_contact, font=("goudy old style", 15, "bold"),bg="lightyellow").place(x=210, y=190, width=220)


        ##-----row4----##
        lbl_desc = Label(self.root, text="Description", font=("goudy old style", 15, "bold"), bg="#898AA6").place(x=50,y=240)

        self.txt_desc = Text(self.root, font=("goudy old style", 15, "bold"), bg="lightyellow")
        self.txt_desc.place(x=210, y=240, width=490, height=140)

        ##----button---##
        
        btn_save = customtkinter.CTkButton(
            self.root,
            text="Save",
            command=self.add,  
            font=("groud old style", 15, "bold"),  
            bg_color="#898AA6",
            fg_color="blue",
            cursor="hand2",
            width=110,  
            height=35
        )
        btn_save.place(x=170, y=370)
        
        
        btn_update = customtkinter.CTkButton(
            self.root,
            text="Update",
            command=self.update, 
            font=("groud old style", 15, "bold"),  
            bg_color="#898AA6",
            fg_color="blue",
            cursor="hand2",
            width=110,  
            height=35
        )
        btn_update.place(x=270, y=370)
        

        btn_delete = customtkinter.CTkButton(
            self.root,
            text="Delete",
            command=self.delete, 
            font=("groud old style", 15, "bold"),  
            bg_color="#898AA6",
            fg_color="blue",
            cursor="hand2",
            width=110,  
            height=35
        )
        btn_save.place(x=370, y=370)

        btn_clear = customtkinter.CTkButton(
            self.root,
            text="Clear",
            command=self.clear,  
            font=("groud old style", 15, "bold"),  
            bg_color="#898AA6",
            fg_color="blue",
            cursor="hand2",
            width=110,  
            height=35
        )
        btn_save.place(x=470, y=370)

        ##---Supplier Table---##

        supp_frame = Frame(self.root, bd=3, relief=RIDGE)
        supp_frame.place(x=900, y=140, width=450, height=460)
        scrolly = Scrollbar(supp_frame, orient=VERTICAL)
        scrollx = Scrollbar(supp_frame, orient=HORIZONTAL)

        self.supplierTable = ttk.Treeview(supp_frame, columns=("invoice", "name", "contact"),yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.supplierTable.xview)
        scrolly.config(command=self.supplierTable.yview)

        self.supplierTable.heading("invoice", text="Invoice No.")
        self.supplierTable.heading("name", text="Name")
        self.supplierTable.heading("contact", text="Contact")
        self.supplierTable.heading("desc", text="Description")
        self.supplierTable["show"] = "headings"
        self.supplierTable.column("invoice", width=90)
        self.supplierTable.column("name", width=120)
        self.supplierTable.column("contact", width=120)
        self.supplierTable.column("desc", width=200)
        self.supplierTable.pack(fill=BOTH, expand=1)
        self.supplierTable.bind("<ButtonRelease-1>",self.get_data)  # bind is type of event on selecting will invoke a function

        self.show()

    ##--------------------------------Func Query----------------------------##
    ##---Insert--##
    def add(self):
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            number = r'\d+'
            contact = r'\d{10}'
            name = r'\D+[^!@#$%&*()_>?":]'
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice must be required ", parent=self.root)
            if(re.fullmatch(number,str(self.var_sup_invoice.get()))):
                if(re.fullmatch(name,str(self.var_sup_name.get()))):
                    if(re.fullmatch(contact,str(self.var_sup_contact.get()))):
                        cur.execute("Select * from supplier where invoice=?", (self.var_sup_invoice.get(),))
                        row = cur.fetchone()
                        if row != None:
                            messagebox.showerror("Error", "This Invoice no. Already Assigned,try different", parent=self.root)
                        else:
                            cur.execute("Insert into supplier (invoice,name,contact,desc) values(?,?,?,?)",
                                        (
                                            self.var_sup_invoice.get(),
                                            self.var_sup_name.get(),
                                            self.var_sup_contact.get(),
                                            self.txt_desc.get('1.0', END),
                                        ))
                            con.commit()
                            messagebox.showinfo("Success", "Supplier Added Successfully !!", parent=self.root)
                            self.show()
                    else:
                        messagebox.showerror("Error","Invalid Contact Number",parent=self.root)
                else:
                    messagebox.showerror("Error","Invalid Name",parent=self.root)
            else:
                messagebox.showerror("Error","Invalid Invoice",parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    ##---show data--##
    def show(self):
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select * from supplier")
            rows = cur.fetchall()
            self.supplierTable.delete(*self.supplierTable.get_children())  # delete all children(value)
            for row in rows:
                self.supplierTable.insert('', END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    ##=---getData---##
    def get_data(self, ev):
        f = self.supplierTable.focus()
        content = (self.supplierTable.item(f))
        row = content['values']
        self.var_sup_invoice.set(row[0])
        self.var_sup_name.set(row[1])
        self.var_sup_contact.set(row[2])
        self.txt_desc.delete('1.0', END)
        self.txt_desc.insert(END, row[3])

    ##---Update Data---##
    def update(self):
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice no. Required ", parent=self.root)
            else:
                cur.execute("Select * from supplier where invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row == None:
                    messagebox.showerror("Error", "Invalid Invoice no.", parent=self.root)
                else:
                    cur.execute("Update  supplier set name=?,contact=?,desc=?  where invoice=?",
                        (
                            self.var_sup_name.get(),
                            self.var_sup_contact.get(),
                            self.txt_desc.get('1.0', END),
                            self.var_sup_invoice.get(),
                        ))
                    con.commit()
                    messagebox.showinfo("Success", "Supplier Updated Successfully !!", parent=self.root)
                    self.show()

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    ##---delete data---##
    def delete(self):
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice no. Required ", parent=self.root)
            else:
                cur.execute("Select * from supplier where invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row == None:
                    messagebox.showerror("Error", "Invalid  Invoice no.", parent=self.root)
                else:
                    op = messagebox.askyesno("Confirmation", "Do you really want to Delete")
                    if op == True:
                        cur.execute("delete from supplier where invoice=?", (self.var_sup_invoice.get(),))
                        con.commit()
                        messagebox.showinfo("Success", "Supplier Deleted Successfully", parent=self.root)
                        self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    ##---Clear Data---##
    def clear(self):
        self.var_sup_invoice.set("")
        self.var_sup_name.set("")
        self.var_sup_contact.set("")
        self.txt_desc.delete('1.0', END)
        self.var_sup_srchtxt.set("")
        self.show()

    ##---Search---##
    def Search(self):
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_srchtxt.get() == "":
                messagebox.showerror("Error", "Invoice no. should be required", parent=self.root)
            else:
                cur.execute("select * from supplier where  invoice=?",(self.var_sup_srchtxt.get(),))
                row = cur.fetchone()
                if row!=None:
                    self.supplierTable.delete(*self.supplierTable.get_children())  # delete all children(value)
                    self.supplierTable.insert('', END, values=row)
                else:
                    messagebox.showerror("Error", "No Record Found ", parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)


if __name__ == "__main__":
    root = customtkinter.CTk()
    obj = supplierClass(root)
    root.mainloop()