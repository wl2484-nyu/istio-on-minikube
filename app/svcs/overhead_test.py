import time
import timeit

import requests

REPEAT = 50
URL = "http://localhost/{}/v1/{}"
MAKE_REQUEST = 'import requests\nresponse = requests.get(url="{}", headers={{"Host": "app-{}.dtp.org"}})'


def make_request(svc, api):
    response = requests.get(
        url=URL.format(svc, api),
        headers={"Host": "app-{}.dtp.org".format(svc)})
    return response.json()


def main():
    for svc, api in [
        ('a', 'a1'), ('a', 'a2'), ('a', 'a3'),
        ('b', 'b1'), ('b', 'b2'),
        ('c', 'c1'), ('c', 'c2'),
        ('d', 'd1'), ('d', 'd2'),
        ('e', 'e1'), ('e', 'e2'),
        ('f', 'f1'), ('f', 'f2'),
        ('g', 'g1'), ('g', 'g2'),
        ('g', 'g1'), ('g', 'g2'),
        ('f', 'f1'), ('f', 'f2'),
        ('e', 'e1'), ('e', 'e2'),
        ('d', 'd1'), ('d', 'd2'),
        ('c', 'c1'), ('c', 'c2'),
        ('b', 'b1'), ('b', 'b2'),
        ('a', 'a1'), ('a', 'a2'), ('a', 'a3')
    ]:
        # timeit_result = timeit.timeit(lambda: make_request(svc, api), number=100)
        # print("/{}/v1/{}: {:.5f} sec per call ()".format(svc, api, timeit_result))
        result = list()

        for i in range(-1, 2):
            # w/o decorators
            api += "n"
            times = timeit.repeat(stmt=MAKE_REQUEST.format(URL.format(svc, api), svc), number=1, repeat=REPEAT)
            if i >= 0:
                result.append([max(times) * 1000, sum(times) * 1000 / len(times), min(times) * 1000])
                print("/{}/v1/{} [{}]: [max, avg, min] = [{:10.2f} , {:10.2f} , {:10.2f} ] ms per call".format(
                    svc, api, 'N', result[i*2][0], result[i*2][1], result[i*2][2]))
            time.sleep(10)

            # w/ decorators
            api = api[:-1]
            times = timeit.repeat(stmt=MAKE_REQUEST.format(URL.format(svc, api), svc), number=1, repeat=REPEAT)
            if i >= 0:
                result.append([max(times) * 1000, sum(times) * 1000 / len(times), min(times) * 1000])
                print("/{}/v1/{}  [{}]: [max, avg, min] = [{:10.2f} , {:10.2f} , {:10.2f} ] ms per call".format(
                    svc, api, 'Y', result[i*2+1][0], result[i*2+1][1], result[i*2+1][2]))
            time.sleep(10)

        N = [(result[0][0] + result[2][0]) / 2.0, (result[0][1] + result[2][1]) / 2.0, (result[0][2] + result[2][2]) / 2.0]
        Y = [(result[1][0] + result[3][0]) / 2.0, (result[1][1] + result[3][1]) / 2.0, (result[1][2] + result[3][2]) / 2.0]
        print("/{}/v1/{} [{}]: [max, avg, min] = [{:10.2f} , {:10.2f} , {:10.2f} ] ms per call".format(
            svc, api + "n", 'N', N[0], N[1], N[2]))
        print("/{}/v1/{}  [{}]: [max, avg, min] = [{:10.2f} , {:10.2f} , {:10.2f} ] ms per call".format(
            svc, api, 'Y', Y[0], Y[1], Y[2]))
        print("/{}/v1/{}     : [max, avg, min] = [{:10.2f}%, {:10.2f}%, {:10.2f}%] overhead".format(
            svc, api, (Y[0] - N[0]) / N[0] * 100, (Y[1] - N[1]) / N[1] * 100, (Y[2] - N[2]) / N[2] * 100))
        time.sleep(30)


if __name__ == '__main__':
    main()
