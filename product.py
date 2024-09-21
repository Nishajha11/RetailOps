from tkinter import*
from PIL import Image,ImageTk
from tkinter import ttk,messagebox
import sqlite3
import re

class productClass:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1100x500+220+130")
        self.root.title("Inventory Management System | Developed by NDV ")
        self.root.config(bg="white")
        self.root.focus_force()

        # All variables
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()
        self.var_pid = StringVar()  # Add this line to define the var_pid attribute
        self.var_cat = StringVar()
        self.var_sup = StringVar()
        self.cat_list = []
        self.sup_list = []
        self.fetch_cat_sup()
        self.var_name = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_status = StringVar()
        
   
#product_frame
        product_Frame=Frame(self.root,bd=2,relief=RIDGE)
        product_Frame.place(x=10,y=10,width=700,height=700)
#title
        lbl_title = Label(product_Frame,text="Manage Product Details",font=("goudy old style",18),bg="#0f4d7d",fg="white").pack(side=TOP,fill=X)

        lbl_category=Label(product_Frame,text="Category",font=("goudy old style",30)).place(x=30,y=60)
        lbl_supplier = Label(product_Frame,text="Supplier",font=("goudy old style",30)).place(x=30,y=130)
        lbl_product_name=Label(product_Frame,text="Name",font=("goudy old style",30)).place(x=30,y=200)
        lbl_price=Label(product_Frame,text="Price",font=("goudy old style",30)).place(x=30,y=270)
        lbl_qty=Label(product_Frame,text="Quantity",font=("goudy old style",30)).place(x=30,y=340)
        lbl_status = Label(product_Frame,text="Status",font=("goudy old style",30)).place(x=30,y=410)
        
        
        #txt_category=Label(product_Frame,text="category",font=("goudy old style",18),bg="white").place(x=30,y=60)
        #options
        
        cmb_cat=ttk.Combobox(product_Frame,textvariable=self.var_cat,values=self.cat_list,state='readonly',justify=CENTER, font=("goudy old style",18))
        cmb_cat.place(x=230,y=70,width=300,height=40)
        cmb_cat.current(0)
        # --supplier combobox--#
        cmb_sup=ttk.Combobox(product_Frame,textvariable=self.var_sup,values=self.sup_list,state='readonly',justify=CENTER, font=("goudy old style",18))
        cmb_sup.place(x=230,y=140,width=300,height=40)
        cmb_sup.current(0)

        #--Product name price
        txt_product=Entry(product_Frame,textvariable=self.var_name, font=("goudy old style",18),bg="white").place(x=230,y=210,width=300,height=40)
        txt_price=Entry(product_Frame,textvariable=self.var_price, font=("goudy old style",18),bg="white").place(x=230,y=280,width=300,height=40)
        txt_qty=Entry(product_Frame,textvariable=self.var_qty, font=("goudy old style",18),bg="white").place(x=230,y=350,width=300,height=40)

        #--status--#
        cmb_status=ttk.Combobox(product_Frame,textvariable=self.var_status,values=("Active","Inactive"),state='readonly',justify=CENTER, font=("goudy old style",18))
        cmb_status.place(x=230,y=420,width=300,height=40)
        cmb_status.current(0)

        #---Button---#
        btn_add=Button(product_Frame,text="SAVE",command=self.add ,font=("goudy old style",15),bg="#2196f3",cursor="hand2").place(x=30,y=500,width=150,height=60)
        btn_update=Button(product_Frame,text="UPDATE",command=self.update,font=("goudy old style",15),bg="red",cursor="hand2").place(x=200,y=500,width=150,height=60)
        btn_delete=Button(product_Frame,text="DELETE",command=self.delete,font=("goudy old style",15),bg="green",cursor="hand2").place(x=370,y=500,width=150,height=60)
        btn_clear=Button(product_Frame,text="CLEAR",command=self.clear ,font=("goudy old style",15),bg="grey",cursor="hand2").place(x=540,y=500,width=150,height=60)

#searchFrame
        lbl_SearchFrame = LabelFrame(self.root, text="Search Product", font=("goudy old style", 25), bd=2, relief=RIDGE, bg="white")
        lbl_SearchFrame.place(x=750,y=10,width=500,height=120)

#options
        cmb_search = ttk.Combobox(lbl_SearchFrame, textvariable=self.var_searchby, values=("Select", "Category", "Supplier", "Name"), state="readonly", justify=CENTER, font=("goudy old style",20))
        cmb_search.place(x=10,y=20,width=250,height=45)
        cmb_search.current(0)
        txt_search = Entry(lbl_SearchFrame,textvariable=self.var_searchtxt,font=("goudy old style",18),bg="lightyellow").place(x=270,y=20,width=250,height=45)
        btn_search = Button(lbl_SearchFrame,text="Search",command=self.Search,font=("goudy old style",18),bg="#4caf50",fg="white",cursor="hand2").place(x=530,y=20,width=150,height=45)



#product details
        p_frame=Frame(self.root,bd=3,relief=RIDGE)
        p_frame.place(x=750,y=200,width=500,height=390)
        scrolly=Scrollbar(p_frame,orient=VERTICAL)
        scrollx=Scrollbar(p_frame,orient=HORIZONTAL)
        self.product_table=ttk.Treeview(p_frame,columns=("pid","Supplier","Category","name","price","qty","status"),yscrollcommand=scrolly.set,xscrollcommand=scrollx.set)
        scrollx.pack(side=BOTTOM,fill=X)
        scrolly.pack(side=RIGHT,fill=Y)
        scrollx.config(command=self.product_table.xview)
        scrolly.config(command=self.product_table.yview)

        self.product_table.heading("pid",text="Product ID")
        self.product_table.heading("Category", text="Category")
        self.product_table.heading("Supplier", text="Supplier")
        self.product_table.heading("name", text="Name")
        self.product_table.heading("price", text="Price")
        self.product_table.heading("qty", text="Quantity")
        self.product_table.heading("status", text="Status")
        self.product_table["show"]="headings"

        self.product_table.column("pid", width=90)
        self.product_table.column("Category", width=100)
        self.product_table.column("Supplier", width=100)
        self.product_table.column("name", width=100)
        self.product_table.column("price", width=100)
        self.product_table.column("qty", width=100)
        self.product_table.column("status", width=100)
        self.product_table.pack(fill=BOTH,expand=1)
        self.product_table.bind("<ButtonRelease-1>",self.get_data)  #bind is type of event on selecting will invoke a function

        self.show()

    ##-------Functions-------##
    def fetch_cat_sup(self):
        self.cat_list.append("Empty")
        self.sup_list.append("Empty")
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("Select name from category")
            cat = cur.fetchall()
            if len(cat) > 0:
                del self.cat_list[:]
                self.cat_list.append("Select")
                for i in cat:
                    self.cat_list.append(i[0])

            cur.execute("select name from supplier")
            sup = cur.fetchall()
            if len(sup) > 0:

                del self.sup_list[:]
                self.sup_list.append("Select")
                for i in sup:
                    self.sup_list.append(i[0])


        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

##---Insert--##
    def add(self):
        con=sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            name = r'\D+[^!@#$%&*()_>?":]'
            num = r'\d+'
            if self.var_cat.get()=="Select" or self.var_cat.get()=="Empty" or self.var_sup.get()=="Select" or self.var_sup.get()=="Empty" or self.var_name.get()=="":
                messagebox.showerror("Error","All fields are required ",parent=self.root)
            if(re.fullmatch(name,str(self.var_name.get()))):
                if(re.fullmatch(num,str(self.var_price.get()))):
                    if (re.fullmatch(num, str(self.var_qty.get()))):
                        cur.execute("Select * from product where name=?",(self.var_name.get(),))
                        row=cur.fetchone()
                        if row!=None:
                             messagebox.showerror("Error","This Product Already Exist,try different",parent=self.root)
                        else:
                            cur.execute("Insert into product (Supplier,Category,name,price,qty,status) values(?,?,?,?,?,?)",(
                                
                                self.var_sup.get(),
                                self.var_cat.get(),
                                self.var_name.get(),
                                self.var_price.get(),
                                self.var_qty.get(),
                                self.var_status.get(),
                            ))
                            con.commit()
                            messagebox.showinfo("Success","Product Added Successfully !!",parent=self.root)
                            self.show()
                    else:
                        messagebox.showerror("Error","Invalid Quantity",parent=self.root)
                else:
                    messagebox.showerror("Error","Invalid Price",parent=self.root)
            else:
                messagebox.showerror("Error","Invalid Name",parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error",f"Error due to : {str(ex)}",parent=self.root)

    ##---show data--##
    def show(self):
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select * from product")
            rows=cur.fetchall()
            self.product_table.delete(*self.product_table.get_children()) #delete all children(value)
            for row in rows:
                self.product_table.insert('',END,values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    ##---getData---##
    def get_data(self,ev):
        f=self.product_table.focus()
        content=(self.product_table.item(f))
        row=content['values']
        self.var_pid.set(row[0]),
        self.var_cat.set(row[1]),
        self.var_sup.set(row[2]),
        self.var_name.set(row[3]),
        self.var_price.set(row[4]),
        self.var_qty.set(row[5]),
        self.var_status.set(row[6]),

    ##---Update Data---##
    def update(self):
        con=sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_pid.get()=="":
                messagebox.showerror("Error","Please Select Product From List ",parent=self.root)
            else:
                cur.execute("Select * from product where pid=?",(self.var_pid.get(),))
                row=cur.fetchone()
                if row==None:
                    messagebox.showerror("Error","Invalid Product ID",parent=self.root)
                else:
                    cur.execute("Update  product set Category=?,Supplier=?,name=?,price=?,qty=?,status=?  where pid=?",(
                                    self.var_cat.get(),
                                    self.var_sup.get(),
                                    self.var_name.get(),
                                    self.var_price.get(),
                                    self.var_qty.get(),
                                    self.var_status.get(),
                                    self.var_pid.get(),
                    ))
                    con.commit()
                    messagebox.showinfo("Success","Product Updated Successfully !!",parent=self.root)
                    self.show()

        except Exception as ex:
            messagebox.showerror("Error",f"Error due to : {str(ex)}",parent=self.root)


    ##---delete data---##
    def delete(self):
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_pid.get()=="":
                messagebox.showerror("Error","Please Select Product From List ",parent=self.root)
            else:
                cur.execute("Select * from product where pid=?",(self.var_pid.get(),))
                row=cur.fetchone()
                if row==None:
                    messagebox.showerror("Error","Invalid Product ID",parent=self.root)
                else:
                    op = messagebox.askyesno("Confirmation", "Do you really want to Delete")
                    if op == True:
                        cur.execute("delete from product where pid=?",(self.var_pid.get(),))
                        con.commit()
                        messagebox.showinfo("Success","Product Deleted Successfully",parent=self.root)
                        self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)


    ##---Clear Data---##
    def clear(self):
        self.var_pid.set("")
        self.var_cat.set("Select")
        self.var_sup.set("Select")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_searchtxt.set("")
        self.var_searchby.set("Select")
        self.show()

    ##---Search---##
    def Search(self):
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_searchby.get()=="Select":
                messagebox.showerror("Error","Select Search by option",parent=self.root)
            elif self.var_searchtxt.get()=="":
                messagebox.showerror("Error","Search input should be required",parent=self.root)
            else:
                cur.execute("select * from product where "+self.var_searchby.get()+" LIKE '%"+self.var_searchtxt.get()+"%'")
                rows = cur.fetchall()
                if len(rows)!=0:
                    self.product_table.delete(*self.product_table.get_children())  # delete all children(value)
                    for row in rows:
                         self.product_table.insert('', END, values=row)
                else:
                    messagebox.showerror("Error","No Record Found ",parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

if __name__=="__main__":
    root=Tk()
    obj=productClass(root)
    root.mainloop()

