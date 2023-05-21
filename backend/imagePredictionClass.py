# declare arrays to store the errors for top, left, bottom, right
def getPassRef(error, final):
    for i in range(len(error)):
        if final[i] < error[i]* 3.5:
            final[i] = error[i] * 3.5
    return final

# for live video
class MSEStabilization:
    def __init__(self, errors, passRef, numParts) -> None:
        self.errors = errors
        self.passRef = passRef
        
        # the number of parts that we have at this station
        self.numParts = numParts
    
    def result(self) -> list:
        # declare the result to store the string "pass" or "fail"
        totalResultStr = []
        totalResultBool = []
        for i in range(self.numParts):
            ans = self.errors[i] - self.passRef[i]
            if ans <= 0:
                totalResultBool.append(1)
            else:
                totalResultBool.append(0)
                
        return totalResultBool