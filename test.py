import multiprocessing as mp

def test():
    print("CHILD PROCESS STARTED")
    print("hello from child")

if __name__ == "__main__":
    p = mp.Process(target=test)
    p.start()
    p.join()

    print("exit code:", p.exitcode)