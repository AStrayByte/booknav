import unittest
from epub import find_str_from_cfi_in_epub


class TestCFI(unittest.TestCase):

    def test_find_str_from_cfi_in_epub2(self):
        cfi = """/6/4[chap01ref]!/4[body01]/10[para05]/1:0"""
        epub_path = "test_books/test.epub"
        str_found = find_str_from_cfi_in_epub(epub_path, cfi,)
        self.assertEqual(str_found, "xxx")
    
    def test_alice_epub(self):
        cfi = """/6/14!/4/2[pgepubid00007]/104/1:0"""
        epub_path = "test_books/AliceInWonderland.epub"
        str_found = find_str_from_cfi_in_epub(epub_path, cfi,)
        self.assertEqual(str_found, "\n“Serpent!” screamed the Pigeon.\n")
    
    def test_alice_kepub(self):
        cfi = """/6/14!/4/2[book-columns]/2[book-inner]/2[pgepubid00007]/104/2[kobo.52.1]/1:0"""
        epub_path = "test_books/AliceInWonderland_converted.kepub.epub"
        str_found = find_str_from_cfi_in_epub(epub_path, cfi,)
        self.assertEqual(str_found, "\n“Serpent!” ")

    def test_frankenstein_epub(self):
        cfi = """/6/18!/4/2[pgepubid00008]/26,/1:1,/1:31"""
        epub_path = "test_books/Frankenstein.epub"
        str_found = find_str_from_cfi_in_epub(epub_path, cfi,)
        self.assertEqual(str_found[:32], "\nNor were these my only visions.")
    
    def test_frankenstein_kepub(self):
        cfi = """/26/30!/4/2[book-columns]/2[book-inner]/2[pgepubid00014]/30/2[kobo.15.1],/1:1,/1:45"""
        epub_path = "test_books/Frankenstein_converted.kepub.epub"
        str_found = find_str_from_cfi_in_epub(epub_path, cfi,)
        self.assertEqual(str_found[:32], "\nThis was strange and unexpected")

if __name__ == "__main__":
    print("Running test_cfi.py")
    unittest.main()