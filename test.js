function fib(n){
    if(n <= 1){
        return n;
    }

    return fib(n-1) + fib(n-2);
}

let arr = [fib(5), fib(6), fib(7)];

console.log(arr.join(","));