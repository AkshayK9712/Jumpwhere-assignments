from collections import Counter

def parse_log_file(filename):
    status_counts = {}
    url_counts = Counter()
    total_requests = 0
    error_requests = 0

    try:
        with open(filename, "r", encoding="utf-8") as file:
            for line in file:
                try:
                    line = line.strip()

                    if not line:
                        continue

                    # Expected format:
                    # GET /index.html 200
                    parts = line.split()

                    if len(parts) < 3:
                        raise ValueError("Malformed log line")

                    method = parts[0]
                    url = parts[1]
                    status_code = int(parts[2])

                    total_requests += 1

                    # Count status codes
                    status_counts[status_code] = status_counts.get(status_code, 0) + 1

                    # Count errors (4xx and 5xx)
                    if 400 <= status_code <= 599:
                        error_requests += 1

                    # Count URLs
                    url_counts[url] += 1

                except (ValueError, IndexError):
                    # Skip malformed lines
                    continue

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return

    # Calculate error percentage
    if total_requests > 0:
        error_percentage = (error_requests / total_requests) * 100
    else:
        error_percentage = 0

    # Report
    print("\n===== Server Log Report =====")

    print("\nStatus-Code Counts:")
    for status_code in sorted(status_counts):
        print(f"{status_code}: {status_counts[status_code]}")

    print(f"\nTotal Requests: {total_requests}")
    print(f"Errors (4xx/5xx): {error_requests}")
    print(f"Error Percentage: {error_percentage:.2f}%")

    print("\nTop 3 URLs:")
    for url, count in url_counts.most_common(3):
        print(f"{url}: {count}")


# Run the program
filename = input("Enter log file name: ")
parse_log_file(filename)