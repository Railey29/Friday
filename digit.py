

def digitTodigitWord(num):
    digit_number = {
    "1" : "one",
    "2": "two",
    "3": "three",
    "4" : "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}
    number = str(num)
    output = []

    for i in range(0 , len(number)):
        output.append(digit_number.get(number[i]))
    
    result = ".".join(output)
    result_final = f"Num.{result}"
    return result_final

print(digitTodigitWord(731))