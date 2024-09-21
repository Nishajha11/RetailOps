from tkinter import*
from PIL import ImageTk
from tkinter import messagebox
import os

class Login_system:
        def __init__(self,root):
               self.root=root
               self.root.title("Login System| Developed by NDV" )
               self.root.geometry("1350x700+0+0")
               self.root.config(bg="#fafafa")

#login
               login_frame=Frame(self.root,bd=2,relief=RIDGE,bg="#010c48")
               login_frame.place(x=470,y=90,width=370,height=460)
        
               title=Label(login_frame,text="RetailOps",font=("Elephant",30,"bold"),fg="white",bg="#010c48").place(x=0,y=30,relwidth=1)
        
               lbl_user=Label(login_frame,text="Username",font=("Andalus",15),fg="white",bg="#010c48").place(x=50,y=120)
               self.username=StringVar()
               self.password=StringVar()
               txt_username=Entry(login_frame,textvariable=self.username,font=("times new roman",15),bg="#ECECEC").place(x=50,y=160,width=250)

               lbl_pass=Label(login_frame,text="Password",font=("Andalus",15),fg="white",bg="#010c48").place(x=50,y=200)
               txt_pass=Entry(login_frame,textvariable=self.password,show="*",font=("times new roman",15),bg="#ECECEC").place(x=50,y=240,width=250)

               btn_login=Button(login_frame,command=self.login,text="Log In",font=("Arial Rounded MT Bold",15),bg="yellow",activebackground="white",fg="black",activeforeground="white",cursor="hand2").place(x=50,y=300,width=250,height=35)
        
               hr=Label(login_frame,bg="lightgray").place(x=50,y=370,width=250,height=2)
               or_=Label(login_frame,text="OR",bg="white",fg="black",font=("times new roman",15,"bold")).place(x=150,y=360)

               btn_forget=Button(login_frame,text="Forget Password?",font=("times new roman",13),fg="white",bg="#010c48",bd=0,activebackground="#010c48",activeforeground="#00759E").place(x=100,y=400)

#frame
               register_frame=Frame(self.root,bd=2,relief=RIDGE,bg="#010c48")
               register_frame.place(x=470,y=570,width=370,height=60)
               lbl_reg=Label(register_frame,text="Don't have an account?",font=("times new roman",13),fg="white",bg="#010c48").place(x=45,y=20)
               btn_singup=Button(register_frame,text="Sign Up",font=("times new roman",13,"bold"),fg="white",bg="#010c48",bd=0,activebackground="#010c48",activeforeground="#00759E").place(x=205,y=17)
        def login(self):
                if self.username.get()=="" or self.password .get()=="":
                        messagebox.showerror("Error","Enter correct info")
                elif self.username.get() != "Divyal" or self.password.get() != "123456":
                        messagebox.showerror("Error","Invalid User or Password\nTry again")
                else:
                        self.root.destroy()
                        os.system("python dashboard.py")

                        
root = Tk()
obj = Login_system(root)
root.mainloop()