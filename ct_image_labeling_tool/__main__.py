import tkinter as tk
from tkinterdnd2 import TkinterDnD

from app import ImageLabelingApp

def init_tkdnd(root):
    try:
        root.tk.call('package', 'require', 'tkdnd')
        print("[INFO] tkdnd 패키지 로드 성공")
        root.tk.call('namespace', 'eval', '::tkdnd', '')
        print("[INFO] 네임스페이스 초기화 완료")
    except tk.TclError as e:
        print(f"[ERROR] tkdnd 초기화 실패: {e}")
        raise RuntimeError('Unable to load tkdnd library.')

def main():
    root = TkinterDnD.Tk()
    root.title("CT Image Labeling Tool")
    root.geometry("1600x800")

    init_tkdnd(root)

    ImageLabelingApp(root)
    
    root.mainloop()

if __name__ == "__main__":
    main()