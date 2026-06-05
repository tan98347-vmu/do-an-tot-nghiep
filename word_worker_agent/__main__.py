from word_worker_agent.master_loop import WordWorkerMaster


def main():
    WordWorkerMaster().run_forever()


if __name__ == '__main__':
    main()
