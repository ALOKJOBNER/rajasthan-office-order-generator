import os
import math
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageOps
from modules.pl_surrender import open_pl_window
from modules.increment_order import open_increment_window
from modules.sanchalan_portal import open_sanchalan_window

class DynamicDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर सॉफ्टवेयर")
        
        # विंडो को फुल स्क्रीन (Maximized) खोलना (तीनों बटन चालू रहेंगे)
        try:
            self.root.state('zoomed')
        except Exception:
            self.root.geometry("1280x800")
        
        self.root.configure(bg="#0c1d36")
        self.angle = 0

        self.setup_ui()
        self.load_profile_image()
        self.animate_rays()

    def setup_ui(self):
        # 1. मुख्य हेडर बैनर
        header_frame = tk.Frame(self.root, bg="#102a45", height=90, relief="ridge", bd=2)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        lbl_title = tk.Label(
            header_frame, 
            text="राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर सॉफ्टवेयर", 
            font=("Segoe UI", 24, "bold"), 
            fg="#f4d03f", 
            bg="#102a45"
        )
        lbl_title.pack(pady=(12, 2))

        lbl_sub = tk.Label(
            header_frame, 
            text="शासकीय एवं प्रशासनिक आदेश स्वचालन प्रणाली (Rajasthan Service Rules Compliant)", 
            font=("Segoe UI", 11, "italic"), 
            fg="#d5dbdb", 
            bg="#102a45"
        )
        lbl_sub.pack()

        # 2. मुख्य कंटेनर
        mid_container = tk.Frame(self.root, bg="#0c1d36")
        mid_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=15)

        # बायाँ पैनल (प्रोफ़ाइल व एनीमेशन)
        left_card = tk.Frame(mid_container, bg="#132743", relief="groove", bd=2, width=440)
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15), pady=5)
        left_card.pack_propagate(False)

        # कैनवस का आकार 260x260 ताकि नुकीली किरणें पूरी तरह फैल सकें
        self.canvas_size = 260
        self.canvas = tk.Canvas(
            left_card, 
            width=self.canvas_size, 
            height=self.canvas_size, 
            bg="#132743", 
            highlightthickness=0
        )
        self.canvas.pack(pady=(15, 5))

        lbl_dev_title = tk.Label(left_card, text="★ सॉफ्टवेयर डेवलपर ★", font=("Segoe UI", 12, "bold"), fg="#f39c12", bg="#132743")
        lbl_dev_title.pack(pady=(2, 2))

        lbl_name = tk.Label(left_card, text="आलोक कुमार सिंह", font=("Segoe UI", 17, "bold"), fg="#ffffff", bg="#132743")
        lbl_name.pack()

        lbl_desig = tk.Label(
            left_card, 
            text="वरिष्ठ अध्यापक\nराजकीय उच्च माध्यमिक विद्यालय, रोजड़ी\nपंचायत समिति: सांभर लेक (जयपुर)", 
            font=("Segoe UI", 11), 
            fg="#85c1e9", 
            bg="#132743", 
            justify="center"
        )
        lbl_desig.pack(pady=4)

        contact_frame = tk.Frame(left_card, bg="#0c1d36", padx=10, pady=8, relief="ridge", bd=1)
        contact_frame.pack(fill=tk.X, padx=20, pady=10)

        lbl_mob = tk.Label(contact_frame, text="📞 मोबाइल: 9414818991", font=("Segoe UI", 11, "bold"), fg="#2ecc71", bg="#0c1d36")
        lbl_mob.pack(anchor="w", pady=2)

        lbl_mail = tk.Label(contact_frame, text="✉ ईमेल: alokjobner@gmail.com", font=("Segoe UI", 10, "bold"), fg="#5dade2", bg="#0c1d36")
        lbl_mail.pack(anchor="w", pady=2)

        # दायाँ पैनल (सॉफ्टवेयर कार्य व आदेश मेनू)
        right_panel = tk.Frame(mid_container, bg="#0c1d36")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        about_card = tk.LabelFrame(right_panel, text=" सॉफ्टवेयर के कार्य एवं भावी विस्तार योजना ", font=("Segoe UI", 12, "bold"), fg="#f4d03f", bg="#132743", padx=15, pady=10)
        about_card.pack(fill=tk.X, pady=(0, 15))

        scope_text = (
            "✔ वर्तमान क्षमताएं: उपार्जित अवकाश (PL Surrender) की सटीक नियमानुसार ऑटो-कैलकुलेशन, "
            "वार्षिक सामयिक वेतन वृद्धि (Annual Increment) आदेश, "
            "संचालन पोर्टल (Sanchalan Portal) के माध्यम से वेंडर/बेनिफिशियरी भुगतान स्वीकृति आदेश जनरेशन, "
            "मल्टीपल कार्मिक/वेंडर प्रविष्टि, A4 सटीक बॉर्डर प्रिंट आदेश।\n\n"
            "🚀 भविष्य में संभावित कार्य: कार्यमुक्ति (Relieving) व कार्यग्रहण (Joining) आदेश, "
            "बाल देखरेख अवकाश (CCL) स्वीकृति, स्थायीकरण (Confirmation) आदेश तथा "
            "समस्त वित्तीय व प्रशासनिक स्वीकृतियों का केंद्रीकृत स्वचालन।"
        )
        lbl_scope = tk.Label(about_card, text=scope_text, font=("Segoe UI", 11), fg="#ecf0f1", bg="#132743", justify="left", wraplength=700)
        lbl_scope.pack(anchor="w", pady=4)

        menu_card = tk.LabelFrame(right_panel, text=" कार्यालय आदेश मॉड्यूल चयन करें ", font=("Segoe UI", 12, "bold"), fg="#5dade2", bg="#132743", padx=20, pady=15)
        menu_card.pack(fill=tk.BOTH, expand=True)

        # 1. उपार्जित अवकाश समर्पण मॉड्यूल
        btn_pl = tk.Button(
            menu_card,
            text="1. उपार्जित अवकाश समर्पण (PL Surrender) आदेश जनरेटर ▶",
            font=("Segoe UI", 13, "bold"),
            bg="#1f618d",
            fg="#ffffff",
            activebackground="#2980b9",
            activeforeground="#ffffff",
            cursor="hand2",
            padx=15,
            pady=12,
            anchor="w",
            relief="raised",
            bd=3,
            command=self.launch_pl_module
        )
        btn_pl.pack(fill=tk.X, pady=8)

        # 2. वार्षिक सामयिक वेतन वृद्धि मॉड्यूल
        btn_inc = tk.Button(
            menu_card,
            text="2. वार्षिक सामयिक वेतन वृद्धि (Annual Increment) आदेश जनरेटर ▶",
            font=("Segoe UI", 13, "bold"),
            bg="#27ae60",
            fg="#ffffff",
            activebackground="#2ecc71",
            activeforeground="#ffffff",
            cursor="hand2",
            padx=15,
            pady=12,
            anchor="w",
            relief="raised",
            bd=3,
            command=self.launch_inc_module
        )
        btn_inc.pack(fill=tk.X, pady=8)

        # 3. संचालन पोर्टल भुगतान स्वीकृति आदेश मॉड्यूल (नया)
        btn_sanchalan = tk.Button(
            menu_card,
            text="3. संचालन पोर्टल भुगतान स्वीकृति (Sanchalan Portal Payment Sanction) आदेश ▶",
            font=("Segoe UI", 13, "bold"),
            bg="#d35400",
            fg="#ffffff",
            activebackground="#e67e22",
            activeforeground="#ffffff",
            cursor="hand2",
            padx=15,
            pady=12,
            anchor="w",
            relief="raised",
            bd=3,
            command=self.launch_sanchalan_module
        )
        btn_sanchalan.pack(fill=tk.X, pady=8)

        # 4. कार्यमुक्ति / कार्यग्रहण मॉड्यूल (आगामी)
        btn_relieve = tk.Button(
            menu_card,
            text="4. कार्यमुक्ति / कार्यग्रहण (Relieving / Joining) आदेश [शीघ्र उपलब्ध]",
            font=("Segoe UI", 11),
            bg="#212f3d",
            fg="#a6acaf",
            activebackground="#212f3d",
            activeforeground="#a6acaf",
            cursor="arrow",
            padx=15,
            pady=10,
            anchor="w",
            relief="groove",
            command=lambda: messagebox.showinfo("अपडेट", "यह मॉड्यूल आगामी संस्करण में सक्रिय किया जाएगा।")
        )
        btn_relieve.pack(fill=tk.X, pady=6)

    def load_profile_image(self):
        img_path = None
        for ext in [".jpg", ".png", ".jpeg", ".JPG", ".PNG"]:
            p = f"aloksingh{ext}"
            if os.path.exists(p):
                img_path = p
                break

        target_size = (130, 130)

        if img_path:
            try:
                raw_img = Image.open(img_path).convert("RGBA")
                raw_img = ImageOps.fit(raw_img, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.3))
                
                mask = Image.new("L", target_size, 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, target_size[0], target_size[1]), fill=255)
                
                circular_img = Image.new("RGBA", target_size, (0, 0, 0, 0))
                circular_img.paste(raw_img, (0, 0), mask=mask)
                self.photo_img = ImageTk.PhotoImage(circular_img)
            except Exception:
                self.photo_img = None
        else:
            self.photo_img = None

    def animate_rays(self):
        self.canvas.delete("all")
        cx = self.canvas_size // 2
        cy = self.canvas_size // 2
        
        num_rays = 24
        inner_r = 66

        for i in range(num_rays):
            center_deg = self.angle + (i * (360 / num_rays))
            
            if i % 2 == 0:
                outer_r = 120
                half_base_deg = 5.0
                ray_color = "#f1c40f"
            else:
                outer_r = 95
                half_base_deg = 3.5
                ray_color = "#ff9f43"

            rad_tip = math.radians(center_deg)
            rad_left = math.radians(center_deg - half_base_deg)
            rad_right = math.radians(center_deg + half_base_deg)

            x1 = cx + inner_r * math.cos(rad_left)
            y1 = cy + inner_r * math.sin(rad_left)

            x_tip = cx + outer_r * math.cos(rad_tip)
            y_tip = cy + outer_r * math.sin(rad_tip)

            x2 = cx + inner_r * math.cos(rad_right)
            y2 = cy + inner_r * math.sin(rad_right)

            self.canvas.create_polygon(
                x1, y1, x_tip, y_tip, x2, y2,
                fill=ray_color,
                outline="",
                smooth=False
            )

        self.canvas.create_oval(cx - 67, cy - 67, cx + 67, cy + 67, outline="#f39c12", width=3)

        if self.photo_img:
            self.canvas.create_image(cx, cy, image=self.photo_img)
        else:
            self.canvas.create_oval(cx - 65, cy - 65, cx + 65, cy + 65, fill="#2980b9", outline="#f1c40f", width=2)
            self.canvas.create_text(cx, cy, text="आलोक सिंह", fill="#ffffff", font=("Segoe UI", 12, "bold"))

        self.angle = (self.angle + 1.5) % 360
        self.root.after(35, self.animate_rays)

    def launch_pl_module(self):
        self.root.withdraw()
        open_pl_window(self.root)

    def launch_inc_module(self):
        self.root.withdraw()
        open_increment_window(self.root)

    def launch_sanchalan_module(self):
        self.root.withdraw()
        open_sanchalan_window(self.root)

def main():
    root = tk.Tk()
    app = DynamicDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
