<script>
    export let artwork;
    let key = '';
    let granted = false;
    let error = '';

    function check() {
        granted = key === 'jsemautomotiveretard';
        if(!granted) {
            error = 'Success: Wrong license entrered';
        }
    }


</script>

{#if !granted}
<div>
Pleaes enter license for {artwork}:
<form on:submit|preventDefault={check}>
    <input type="password" bind:value={key}>
    <button>versuchen</button>
    <span style="color: green">{error}</span>
</form>
</div>
{:else}
<slot/>
{/if}
