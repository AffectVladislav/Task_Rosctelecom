from app.parser_rialcom import ParserRialcom


def main():
    data_parser = ParserRialcom()

    result = data_parser.load_data()
    if result == 200:
        data_parser.save_data()

    else:
        print(f"Status Code: {result}")


if __name__ == "__main__":
    main()