from chain import LawCodeUploaderChain


chained_uploader = LawCodeUploaderChain("codes")

if __name__ == "__main__":
    chained_uploader.explore()