from feeds import Fetch

if __name__ == "__main__":
    Fetch.fetch_abusech_to_json()
    Fetch.fetch_circl_to_json()
    Fetch.fetch_otx_to_json()